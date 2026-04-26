import { useEffect, useRef } from 'preact/hooks';
import { drawWorld } from '../render/world.js';
import { clamp, lerp, lerpAngle, smoothstep } from '../utils/math.js';

const DEFAULT_CAMERA = {
  yaw: 0,
  pitch: -0.32,
  distance: 980,
};

function cloneData(data) {
  if (!data) return null;

  return {
    ...data,
    body: data.body ? { ...data.body } : null,
    environment: data.environment
      ? {
          ...data.environment,
          terrain: data.environment.terrain || null,
          food: Array.isArray(data.environment.food)
            ? data.environment.food.map(f => ({ ...f }))
            : [],
        }
      : null,
  };
}

function interpolateData(from, to, t) {
  if (!from || !to || !from.body || !to.body) return to || from;

  const k = smoothstep(t);

  return {
    ...to,
    body: {
      ...to.body,
      x: lerp(from.body.x, to.body.x, k),
      y: lerp(from.body.y, to.body.y, k),
      z: lerp(from.body.z, to.body.z, k),
      yaw: lerpAngle(from.body.yaw, to.body.yaw, k),
      pitch: lerpAngle(from.body.pitch, to.body.pitch, k),
      roll: lerpAngle(from.body.roll, to.body.roll, k),
      energy: lerp(from.body.energy, to.body.energy, k),
    },
  };
}

export function WorldCanvas({ data, camera, setCamera }) {
  const ref = useRef(null);
  const dragRef = useRef(null);
  const cameraRef = useRef(camera);

  const prevFrameRef = useRef(null);
  const nextFrameRef = useRef(null);
  const lastPacketAtRef = useRef(performance.now());
  const packetIntervalRef = useRef(1000 / 30);

  cameraRef.current = camera;

  useEffect(() => {
    if (!data?.body) return;

    const now = performance.now();
    const last = nextFrameRef.current;

    if (last) {
      packetIntervalRef.current = clamp(now - lastPacketAtRef.current, 16, 500);
      prevFrameRef.current = cloneData(last);
    } else {
      prevFrameRef.current = cloneData(data);
    }

    nextFrameRef.current = cloneData(data);
    lastPacketAtRef.current = now;
  }, [data]);

  useEffect(() => {
    const canvas = ref.current;

    if (!canvas) return;

    const onPointerDown = event => {
      canvas.setPointerCapture?.(event.pointerId);

      dragRef.current = {
        x: event.clientX,
        y: event.clientY,
        yaw: cameraRef.current.yaw,
        pitch: cameraRef.current.pitch,
      };
    };

    const onPointerMove = event => {
      const drag = dragRef.current;

      if (!drag) return;

      setCamera(prev => ({
        ...prev,
        yaw: drag.yaw + (event.clientX - drag.x) * 0.006,
        pitch: clamp(drag.pitch + (event.clientY - drag.y) * 0.004, -1.15, 0.75),
      }));
    };

    const onPointerUp = event => {
      dragRef.current = null;
      canvas.releasePointerCapture?.(event.pointerId);
    };

    const onWheel = event => {
      event.preventDefault();

      setCamera(prev => ({
        ...prev,
        distance: clamp(prev.distance + event.deltaY * 0.7, 380, 2200),
      }));
    };

    const onDoubleClick = () => setCamera(DEFAULT_CAMERA);

    canvas.addEventListener('pointerdown', onPointerDown);
    canvas.addEventListener('pointermove', onPointerMove);
    canvas.addEventListener('pointerup', onPointerUp);
    canvas.addEventListener('pointercancel', onPointerUp);
    canvas.addEventListener('wheel', onWheel, { passive: false });
    canvas.addEventListener('dblclick', onDoubleClick);

    return () => {
      canvas.removeEventListener('pointerdown', onPointerDown);
      canvas.removeEventListener('pointermove', onPointerMove);
      canvas.removeEventListener('pointerup', onPointerUp);
      canvas.removeEventListener('pointercancel', onPointerUp);
      canvas.removeEventListener('wheel', onWheel);
      canvas.removeEventListener('dblclick', onDoubleClick);
    };
  }, [setCamera]);

  useEffect(() => {
    let raf;

    const loop = () => {
      const canvas = ref.current;

      if (canvas) {
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;

        const nextWidth = Math.max(1, Math.floor(rect.width * dpr));
        const nextHeight = Math.max(1, Math.floor(rect.height * dpr));

        if (canvas.width !== nextWidth || canvas.height !== nextHeight) {
          canvas.width = nextWidth;
          canvas.height = nextHeight;
        }

        const ctx = canvas.getContext('2d');
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        const elapsed = performance.now() - lastPacketAtRef.current;
        const t = clamp(elapsed / packetIntervalRef.current, 0, 1);
        const smoothData = interpolateData(prevFrameRef.current, nextFrameRef.current, t);

        drawWorld(ctx, smoothData, cameraRef.current, rect.width, rect.height);
      }

      raf = requestAnimationFrame(loop);
    };

    loop();

    return () => cancelAnimationFrame(raf);
  }, []);

  return <canvas class="worldCanvas" ref={ref} />;
}