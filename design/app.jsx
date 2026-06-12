// app.jsx — aperçu branché sur les vrais fichiers assets/*.svg (source unique)
const { useEffect } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "banner": "editorial",
  "accent": "#C2A878",
  "theme": "dark",
  "animate": true
}/*EDITMODE-END*/;

const BANNER_FILES = {
  editorial: "../assets/github-banner.svg",
  centered: "../assets/github-banner-centered.svg",
  spec: "../assets/github-banner-spec.svg"
};

const ACCENTS = ["#C2A878", "#9AB0C4", "#8FAE9B", "#B98C7A", "#E7E5DF"];
const ACCENT_LABEL = {
  "#C2A878": "Champagne",
  "#9AB0C4": "Acier",
  "#8FAE9B": "Sauge",
  "#B98C7A": "Terre",
  "#E7E5DF": "Platine"
};

function badgesHTML() {
  const lbl = "0d1117", col = "161b22";
  const items = [
    ["Tauri%202", "tauri"],
    ["React%2019", "react"],
    ["TypeScript%205", "typescript"],
    ["Rust", "rust"],
    ["Node.js%2024", "nodedotjs"],
    ["Biome", "biome"]
  ];
  return items.map(([t, logo]) =>
    `<img src="https://img.shields.io/badge/${t}-${col}?style=flat-square&logo=${logo}&logoColor=DDD6C9&labelColor=${lbl}" alt="${t}">`
  ).join("");
}

function recolorSvg(svg, accent) {
  if (!accent || accent === "#C2A878") return svg;
  const hex = accent.replace("#", "").toUpperCase();
  return svg
    .replaceAll("#C2A878", accent)
    .replaceAll("#c2a878", accent)
    .replaceAll("C2A878", hex)
    .replaceAll("c2a878", hex.toLowerCase());
}

function stripAnimations(svg) {
  return svg.replace(/<animate[\s\S]*?\/>/g, "");
}

async function loadBannerInto(el, variant, accent, animate, replay) {
  const path = BANNER_FILES[variant] || BANNER_FILES.editorial;
  const res = await fetch(`${path}?t=${replay}`);
  if (!res.ok) throw new Error(`fetch ${path}: ${res.status}`);
  let svg = await res.text();
  svg = recolorSvg(svg, accent);
  if (!animate) svg = stripAnimations(svg);
  const uri = "data:image/svg+xml;utf8," + encodeURIComponent(svg);
  el.innerHTML = '<img alt="DevRedious" style="display:block;width:100%;border-radius:8px" src="' + uri + '">';
}

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [replay, setReplay] = React.useState(0);

  useEffect(() => {
    document.documentElement.style.setProperty("--accent", t.accent);
    document.body.style.setProperty("--accent", t.accent);
    document.body.setAttribute("data-theme", t.theme);
    const b = document.getElementById("banner");
    if (b) {
      loadBannerInto(b, t.banner, t.accent, t.animate, replay).catch((err) => {
        console.error(err);
        b.innerHTML = '<p style="color:#f85149;font-size:13px">Impossible de charger la bannière : ' + err.message + '</p>';
      });
    }
    const bd = document.getElementById("badges");
    if (bd && !bd.dataset.filled) { bd.innerHTML = badgesHTML(); bd.dataset.filled = "1"; }
  }, [t.banner, t.accent, t.theme, t.animate, replay]);

  return (
    <TweaksPanel title="Tweaks">
      <TweakSection label="Bannière" />
      <TweakRadio
        label="Composition"
        value={t.banner}
        options={["editorial", "centered", "spec"]}
        onChange={(v) => setTweak("banner", v)}
      />
      <TweakSection label="Teinte d'accent" />
      <TweakColor
        label="Accent"
        value={t.accent}
        options={ACCENTS}
        onChange={(v) => setTweak("accent", v)}
      />
      <div style={{ fontSize: 11, color: "#8a8a8a", marginTop: -4, paddingLeft: 2 }}>
        {ACCENT_LABEL[t.accent] || ""}
      </div>
      <TweakSection label="Animation" />
      <TweakToggle
        label="Animer la bannière"
        value={t.animate}
        onChange={(v) => setTweak("animate", v)}
      />
      <TweakButton label="Rejouer l'animation" onClick={() => setReplay((n) => n + 1)} />
      <TweakSection label="Rendu GitHub" />
      <TweakRadio
        label="Thème"
        value={t.theme}
        options={["dark", "light"]}
        onChange={(v) => setTweak("theme", v)}
      />
    </TweaksPanel>
  );
}

ReactDOM.createRoot(document.getElementById("tweaks-root")).render(<App />);
