import json, logging, math, os, secrets, hashlib, time
from typing import List, Optional
import httpx
logger = logging.getLogger(__name__)

class EntropyPool:
    def __init__(self, pool_target: int = 4096):
        self.pool: List[float] = []
        self.pool_target = pool_target
        self.local = secrets.SystemRandom()
        self.last_source = "local"
        self.last_refresh_ts = 0.0
    async def refresh(self):
        try:
            values = await self._fetch_random_org()
            if values:
                self.pool.extend(values); self.last_source = "random.org"; self.last_refresh_ts = time.time(); self._trim(); return
        except Exception as e: logger.warning(f"RANDOM.ORG entropy failed: {e}")
        try:
            values = await self._fetch_nist_beacon()
            if values:
                self.pool.extend(values); self.last_source = "nist-beacon"; self.last_refresh_ts = time.time(); self._trim(); return
        except Exception as e: logger.warning(f"NIST Beacon entropy failed: {e}")
        self.last_source = "local"
    async def _fetch_random_org(self) -> Optional[List[float]]:
        api_key = os.getenv("RANDOM_ORG_API_KEY")
        if not api_key: return None
        payload = {"jsonrpc":"2.0","method":"generateDecimalFractions","params":{"apiKey":api_key,"n":512,"decimalPlaces":12,"replacement":True},"id":int(time.time()*1000)}
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post("https://api.random.org/json-rpc/4/invoke", json=payload); r.raise_for_status(); data = r.json()
        if "error" in data: raise RuntimeError(data["error"])
        return [float(x) for x in data["result"]["random"]["data"]]
    async def _fetch_nist_beacon(self) -> Optional[List[float]]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("https://beacon.nist.gov/beacon/2.0/pulse/last"); r.raise_for_status(); data = r.json()
        digest = hashlib.sha512(json.dumps(data, sort_keys=True).encode()).digest()
        return [int.from_bytes(digest[i:i+8], "big") / float(2**64 - 1) for i in range(0, len(digest), 8)]
    def _trim(self):
        if len(self.pool) > self.pool_target: self.pool = self.pool[-self.pool_target:]
    def random(self) -> float:
        if self.pool: return self.pool.pop(0)
        self.last_source = "local"; return self.local.random()
    def uniform(self, a: float, b: float) -> float: return a + (b - a) * self.random()
    def randint(self, a: int, b: int) -> int: return a + int(self.random() * ((b - a) + 1))
    def signed(self) -> float: return self.random() * 2.0 - 1.0
    def gaussian(self, mean=0.0, stdev=1.0) -> float:
        u1=max(1e-12,self.random()); u2=self.random(); return mean + math.sqrt(-2*math.log(u1))*math.cos(2*math.pi*u2)*stdev
GLOBAL_ENTROPY = EntropyPool()
