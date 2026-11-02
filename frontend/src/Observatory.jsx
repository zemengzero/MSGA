import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import ForceGraph3D from "react-force-graph-3d";
import * as THREE from "three";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import {
  Orbit,
  Maximize2,
  Minimize2,
  MoveUpRight,
  Pause,
  Play,
  Focus,
  Sparkles,
} from "lucide-react";
import "./observatory.css";

/*! seededRandom and radial glow adapted from CosmoGraph.
 * Copyright (c) 2026 n1ghtmare-dev. @license MIT
 * Full notice: third_party/cosmograph/LICENSE; embedded in Windows distributions.
 */
function seededRandom(seed) {
  let value = seed >>> 0;
  return () => {
    value += 0x6d2b79f5;
    let output = value;
    output = Math.imul(output ^ (output >>> 15), output | 1);
    output ^= output + Math.imul(output ^ (output >>> 7), output | 61);
    return ((output ^ (output >>> 14)) >>> 0) / 4294967296;
  };
}
const COLORS = [
  "#a5bbff",
  "#b8a0ed",
  "#f1c68a",
  "#70cec2",
  "#efa4c1",
  "#aab7d8",
];
const keyOf = (value) => (typeof value === "object" ? value.id : value);
const escapeLabel = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
function disposeNode(group) {
  group.traverse((object) => {
    object.geometry?.dispose();
    if (object.material) {
      if (object.isSprite) object.material.map?.dispose();
      object.material.dispose();
    }
  });
}
function glowTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 128;
  const ctx = canvas.getContext("2d");
  const gradient = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.12, "rgba(255,255,255,.9)");
  gradient.addColorStop(0.36, "rgba(255,255,255,.24)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(canvas);
}
function planetTexture(color, seed, large = false) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  const base = new THREE.Color(color);
  const image = ctx.createImageData(512, 256);
  const random = seededRandom(seed);
  for (let y = 0; y < 256; y++)
    for (let x = 0; x < 512; x++) {
      const u = x / 512,
        v = y / 256;
      const wave = Math.sin(
        v * 41 + Math.sin(u * 17) * 0.6 + Math.sin(u * 33 + v * 15) * 0.18,
      );
      const clouds =
        Math.sin(u * 19 + Math.sin(v * 18) * 3) * Math.sin(v * 23 + u * 7);
      const light = 0.6 + 0.17 * wave + 0.14 * clouds + random() * 0.07;
      const i = (y * 512 + x) * 4;
      image.data[i] = Math.min(255, base.r * 210 * light + (large ? 35 : 23));
      image.data[i + 1] = Math.min(
        255,
        base.g * 210 * light + (large ? 32 : 19),
      );
      image.data[i + 2] = Math.min(
        255,
        base.b * 225 * light + (large ? 41 : 24),
      );
      image.data[i + 3] = 255;
    }
  ctx.putImageData(image, 0, 0);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}
function nebulaTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 1536;
  canvas.height = 1024;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#030610";
  ctx.fillRect(0, 0, 1536, 1024);
  const random = seededRandom(2909);
  ctx.globalCompositeOperation = "screen";
  for (let i = 0; i < 75; i++) {
    const x = 150 + random() * 1250,
      y = 260 + Math.sin(x / 330) * 130 + (random() - 0.5) * 270;
    const r = 100 + random() * 240;
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(
      0,
      i % 3 === 0 ? "#6d3c5e10" : i % 3 === 1 ? "#2c437d14" : "#7661400c",
    );
    g.addColorStop(1, "#00000000");
    ctx.fillStyle = g;
    ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }
  ctx.globalCompositeOperation = "source-over";
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}
function backgroundScene(scene) {
  const group = new THREE.Group();
  const sky = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: nebulaTexture(),
      depthWrite: false,
      fog: false,
    }),
  );
  sky.position.set(0, 0, -820);
  sky.scale.set(2600, 1500, 1);
  group.add(sky);
  const random = seededRandom(8206);
  const geometry = new THREE.BufferGeometry();
  const positions = [],
    colors = [];
  for (let i = 0; i < 2300; i++) {
    positions.push(
      (random() - 0.5) * 2300,
      (random() - 0.5) * 1450,
      -200 - random() * 1200,
    );
    const c = new THREE.Color(
      i % 4 === 0 ? "#d1ad85" : i % 3 === 0 ? "#849bcf" : "#a9b8d8",
    );
    const lum = 0.25 + random() * 0.75;
    colors.push(c.r * lum, c.g * lum, c.b * lum);
  }
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(positions, 3),
  );
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  const stars = new THREE.Points(
    geometry,
    new THREE.PointsMaterial({
      size: 1.15,
      vertexColors: true,
      transparent: true,
      opacity: 0.83,
      sizeAttenuation: true,
      depthWrite: false,
    }),
  );
  group.add(stars);

  const core = new THREE.Mesh(
    new THREE.SphereGeometry(74, 64, 48),
    new THREE.MeshStandardMaterial({
      map: planetTexture("#c5bbc4", 91, true),
      roughness: 0.83,
      metalness: 0.12,
    }),
  );
  core.rotation.z = 0.2;
  core.position.set(0, -3, -16);
  group.add(core);
  const atmosphere = new THREE.Mesh(
    new THREE.SphereGeometry(78, 48, 32),
    new THREE.ShaderMaterial({
      vertexShader: `varying vec3 n; varying vec3 p; void main(){n=normalize(mat3(modelMatrix)*normal);p=(modelMatrix*vec4(position,1.)).xyz;gl_Position=projectionMatrix*viewMatrix*vec4(p,1.);}`,
      fragmentShader: `varying vec3 n; varying vec3 p; void main(){float f=pow(1.-abs(dot(normalize(n),normalize(cameraPosition-p))),3.8);gl_FragColor=vec4(.65,.52,.88,f*.45);}`,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.BackSide,
    }),
  );
  atmosphere.position.copy(core.position);
  group.add(atmosphere);
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(97, 130, 192),
    new THREE.MeshBasicMaterial({
      color: "#c2a7c9",
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.12,
      depthWrite: false,
    }),
  );
  ring.rotation.set(1.2, 0.28, -0.3);
  ring.position.copy(core.position);
  group.add(ring);
  for (const radius of [94, 111, 133, 144]) {
    const points = Array.from(
      { length: 257 },
      (_, i) =>
        new THREE.Vector3(
          Math.cos((i / 256) * Math.PI * 2) * radius,
          Math.sin((i / 256) * Math.PI * 2) * radius,
          0,
        ),
    );
    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(points),
      new THREE.LineBasicMaterial({
        color: radius === 133 ? "#dec6a4" : "#a0a3c6",
        transparent: true,
        opacity: radius === 133 ? 0.43 : 0.14,
      }),
    );
    line.rotation.copy(ring.rotation);
    line.position.copy(core.position);
    group.add(line);
  }
  const fill = new THREE.AmbientLight("#afb6e0", 1.2);
  group.add(fill);
  const sun = new THREE.DirectionalLight("#fff1dd", 4);
  sun.position.set(-160, 170, 260);
  group.add(sun);
  const rim = new THREE.PointLight("#798cff", 16, 900, 1.2);
  rim.position.set(130, -10, -120);
  group.add(rim);
  const start = performance.now();
  core.onBeforeRender = () => {
    core.rotation.y = (performance.now() - start) * 0.000012;
  };
  scene.add(group);
  return {
    group,
    dispose() {
      scene.remove(group);
      group.traverse((o) => {
        o.geometry?.dispose();
        if (o.material) {
          for (const m of Array.isArray(o.material)
            ? o.material
            : [o.material]) {
            m.map?.dispose();
            m.dispose();
          }
        }
      });
    },
  };
}

export default function Observatory({ graph, matched, query, onOpen, paused }) {
  const ref = useRef(),
    host = useRef(),
    backdrop = useRef(),
    objects = useRef(new Map()),
    textures = useRef(new Map());
  const [instance, setInstance] = useState(null),
    [size, setSize] = useState({ width: 800, height: 610 });
  const [hover, setHover] = useState(null),
    [cinema, setCinema] = useState(false),
    [cruise, setCruise] = useState(false),
    [softLight, setSoftLight] = useState(true);
  const [available, setAvailable] = useState(true);
  const bloom = useRef();
  const hitIds = useMemo(() => new Set(matched), [matched]);
  const data = useMemo(() => {
    const counts = new Map();
    graph.nodes.forEach((n) =>
      n.tags.forEach((t) => counts.set(t, (counts.get(t) || 0) + 1)),
    );
    const domain = (n) =>
      n.tags.find((t) => counts.get(t) <= graph.nodes.length * 0.45) ||
      n.tags[0] ||
      "未分类";
    const groups = [...new Set(graph.nodes.map(domain))].sort();
    const slots = new Map();
    const nodes = graph.nodes.map((n) => {
      const tag = domain(n),
        g = groups.indexOf(tag),
        slot = slots.get(tag) || 0;
      slots.set(tag, slot + 1);
      const angle =
        (g / Math.max(1, groups.length)) * Math.PI * 2 -
        0.5 +
        (slot - 2.5) * 0.09;
      const radius = 155 + (slot % 3) * 21;
      return {
        ...n,
        domain: tag,
        visualColor: COLORS[g % COLORS.length],
        featured: slot === 0,
        fx: Math.cos(angle) * radius,
        fy: Math.sin(angle) * radius * 0.7 + (slot % 2) * 19,
        fz: Math.sin(angle * 1.8) * 42 + slot * 5 - 5,
      };
    });
    return { nodes, links: graph.links.map((l) => ({ ...l })) };
  }, [graph]);
  const neighbours = useMemo(() => {
    const ids = new Set(hover ? [hover] : []);
    for (const link of data.links) {
      const a = keyOf(link.source),
        b = keyOf(link.target);
      if (a === hover) ids.add(b);
      if (b === hover) ids.add(a);
    }
    return ids;
  }, [data, hover]);
  const bind = useCallback((value) => {
    ref.current = value;
    setInstance(value);
  }, []);
  const overview = useCallback(() => {
    ref.current?.cameraPosition(
      { x: 0, y: 30, z: 510 },
      { x: 0, y: 0, z: 0 },
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 900,
    );
  }, []);
  useEffect(() => {
    if (!host.current) return;
    const ro = new ResizeObserver(([entry]) =>
      setSize({
        width: Math.floor(entry.contentRect.width),
        height: Math.floor(entry.contentRect.height),
      }),
    );
    ro.observe(host.current);
    return () => ro.disconnect();
  }, []);
  useEffect(() => {
    if (!instance) return;
    try {
      instance
        .renderer()
        .setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      backdrop.current = backgroundScene(instance.scene());
      instance.cameraPosition({ x: 0, y: 50, z: 660 }, { x: 0, y: 0, z: 0 }, 0);
      const timer = setTimeout(() => {
        overview();
        window.__graphRendered = true;
      }, 150);
      const pass = new UnrealBloomPass(
        new THREE.Vector2(size.width, size.height),
        0.5,
        0.5,
        0.8,
      );
      bloom.current = pass;
      instance.postProcessingComposer().addPass(pass);
      const canvas = instance.renderer().domElement;
      const contextLost = (event) => {
        event.preventDefault();
        setAvailable(false);
      };
      canvas.addEventListener("webglcontextlost", contextLost);
      window.__observatoryReady = true;
      return () => {
        clearTimeout(timer);
        canvas.removeEventListener("webglcontextlost", contextLost);
        window.__observatoryReady = false;
        backdrop.current?.dispose();
        instance.postProcessingComposer().removePass(pass);
        pass.dispose();
      };
    } catch (error) {
      console.error("Observatory setup", error);
      setAvailable(false);
    }
  }, [instance, overview]);
  useEffect(() => {
    if (bloom.current) bloom.current.enabled = softLight;
  }, [softLight, instance]);
  useEffect(() => {
    if (!instance) return;
    instance.controls().autoRotate = cruise && !paused;
    instance.controls().autoRotateSpeed = 0.25;
    if (paused) instance.pauseAnimation();
    else instance.resumeAnimation();
  }, [instance, cruise, paused]);
  useEffect(() => {
    const close = (e) => {
      if (e.key === "Escape") setCinema(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);
  useEffect(
    () => () => {
      objects.current.forEach(disposeNode);
      textures.current.forEach((texture) => texture.dispose());
    },
    [],
  );
  useEffect(() => {
    const present = new Set(data.nodes.map((note) => note.id));
    for (const [id, group] of objects.current) {
      if (!present.has(id)) {
        disposeNode(group);
        objects.current.delete(id);
      }
    }
  }, [data]);
  const makeNode = useCallback(
    (n) => {
      let group = objects.current.get(n.id);
      if (
        group &&
        (group.userData.title !== n.title ||
          group.userData.color !== n.visualColor)
      ) {
        disposeNode(group);
        objects.current.delete(n.id);
        group = null;
      }
      const lit =
        (!query || hitIds.has(n.id)) && (!hover || neighbours.has(n.id));
      if (!group) {
        group = new THREE.Group();
        group.userData = { title: n.title, color: n.visualColor };
        const radius =
          3.7 + Math.min(7, n.degree) * 0.24 + (n.featured ? 1 : 0);
        let texture = textures.current.get(n.visualColor);
        if (!texture) {
          texture = planetTexture(
            n.visualColor,
            41 + n.visualColor.charCodeAt(2),
          );
          textures.current.set(n.visualColor, texture);
        }
        const material = new THREE.MeshStandardMaterial({
          map: texture,
          color: "#ffffff",
          roughness: 0.7,
          metalness: 0.15,
          emissive: n.visualColor,
          emissiveIntensity: 0.3,
          transparent: true,
        });
        group.add(
          new THREE.Mesh(new THREE.SphereGeometry(radius, 24, 18), material),
        );
        const glow = new THREE.Sprite(
          new THREE.SpriteMaterial({
            map: glowTexture(),
            color: n.visualColor,
            transparent: true,
            opacity: 0.27,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
          }),
        );
        glow.scale.setScalar(radius * 6);
        group.add(glow);
        const canvas = document.createElement("canvas");
        canvas.width = 768;
        canvas.height = 96;
        const ctx = canvas.getContext("2d");
        ctx.font = '500 40px "Inter Variable","Microsoft YaHei UI",sans-serif';
        ctx.fillStyle = "#d7d9e8";
        ctx.textAlign = "center";
        ctx.fillText(
          n.title.length > 18 ? n.title.slice(0, 18) + "…" : n.title,
          384,
          48,
        );
        const label = new THREE.Sprite(
          new THREE.SpriteMaterial({
            map: new THREE.CanvasTexture(canvas),
            transparent: true,
            depthWrite: false,
            opacity: 0.8,
          }),
        );
        label.scale.set(150, 20, 1);
        label.position.y = -radius - 9;
        group.add(label);
        objects.current.set(n.id, group);
      }
      group.children[0].material.opacity = lit ? 1 : 0.15;
      group.children[0].material.emissiveIntensity =
        n.id === hover ? 1.1 : 0.55;
      group.children[1].material.opacity = lit
        ? n.id === hover
          ? 0.7
          : 0.28
        : 0.025;
      group.children[2].visible =
        n.featured || n.id === hover || (Boolean(query) && hitIds.has(n.id));
      group.children[2].material.opacity = lit ? 0.95 : 0.14;
      return group;
    },
    [hitIds, hover, neighbours, query],
  );
  const related = (link) =>
    !hover || keyOf(link.source) === hover || keyOf(link.target) === hover;
  const selected = data.nodes.find((n) => n.id === hover);
  return (
    <div
      className={"observatory " + (cinema ? "observatory-cinema" : "")}
      ref={host}
      data-testid="graph-stage"
    >
      <div className="observatory-shade" />
      {available && data.nodes.length > 0 ? (
        <ForceGraph3D
          ref={bind}
          graphData={data}
          width={size.width}
          height={size.height}
          backgroundColor="#040713"
          showNavInfo={false}
          nodeThreeObject={makeNode}
          nodeLabel={(n) => escapeLabel(n.title)}
          nodeRelSize={6}
          linkColor={(link) =>
            hover && related(link) ? "#d3c7de" : hover ? "#161d30" : "#52617e"
          }
          linkOpacity={0.22}
          linkWidth={(link) => (hover && related(link) ? 1.5 : 0.45)}
          linkCurvature={0.12}
          linkDirectionalParticles={(link) => (hover && related(link) ? 3 : 0)}
          linkDirectionalParticleWidth={1.5}
          onNodeHover={(n) => setHover(n?.id || null)}
          onNodeClick={(n) => {
            setCinema(false);
            onOpen(n.id);
          }}
          enableNodeDrag={false}
          warmupTicks={0}
          cooldownTicks={1}
          rendererConfig={{
            antialias: true,
            alpha: true,
            powerPreference: "high-performance",
          }}
        />
      ) : (
        <div className="observatory-empty">
          <Orbit size={52} />
          <h3>{available ? "你的宇宙，始于一个想法" : "图形暂不可用"}</h3>
          <p>
            {available
              ? "新建笔记，让第一颗星亮起来"
              : "可从全部笔记继续阅读与编辑"}
          </p>
        </div>
      )}
      <div className="observatory-caption">
        <span className="obs-live" />
        LIVE CONSTELLATION <span className="obs-coordinate">Z / 01</span>
      </div>
      <div className="observatory-heading">
        <span>THE SPACE BETWEEN IDEAS</span>
        <h2>
          万千想法。
          <br />
          <em>自成宇宙。</em>
        </h2>
        <p>每一道光，都是你留下的思考。</p>
      </div>
      <div className="observatory-orbit-label">
        YOUR IDEAS HAVE GRAVITY <span>✧</span>
      </div>
      <div className="observatory-hover" aria-live="polite">
        {selected ? (
          <>
            <span style={{ background: selected.visualColor }} />
            <strong>{selected.title}</strong>
            <small>
              点击打开笔记 <MoveUpRight size={12} />
            </small>
          </>
        ) : (
          <>
            <span />
            <strong>探索你的知识星系</strong>
            <small>拖动旋转 · 滚轮缩放 · 点击阅读</small>
          </>
        )}
      </div>
      <div className="observatory-controls">
        <button aria-label="图谱居中" title="恢复视角" onClick={overview}>
          <Focus size={16} />
        </button>
        <button
          aria-label={cruise ? "暂停巡航" : "自动巡航"}
          title={cruise ? "暂停巡航" : "自动巡航"}
          className={cruise ? "on" : ""}
          onClick={() => setCruise(!cruise)}
        >
          {cruise ? <Pause size={15} /> : <Play size={15} />}
        </button>
        <button
          aria-label="切换柔光"
          title="柔光效果"
          className={softLight ? "on" : ""}
          onClick={() => setSoftLight(!softLight)}
        >
          <Sparkles size={15} />
        </button>
        <span />
        <button
          aria-label={cinema ? "退出沉浸" : "沉浸展示"}
          title={cinema ? "退出沉浸（Esc）" : "沉浸展示"}
          onClick={() => setCinema(!cinema)}
        >
          {cinema ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
        </button>
      </div>
      <div className="observatory-footer">
        <div>
          <b>{String(data.nodes.length).padStart(2, "0")}</b>
          <span>颗知识星辰</span>
          <i />
          <b>{String(data.links.length).padStart(2, "0")}</b>
          <span>条真实关联</span>
        </div>
        <span>LOCAL-FIRST / ALWAYS YOURS</span>
      </div>
    </div>
  );
}
