/**
 * Cetacean 3D mesh generator for Plotly mesh3d traces.
 *
 * Coordinate system (matches backend compute_trajectory):
 *   heading=0° → +x,  heading=90° → -y
 *   z = depth (positive = deeper)
 *   Plotly zaxis reversed so deeper is visually lower.
 *
 * Body frame (before rotation):
 *   x = nose (+) to tail (-)
 *   y = left (+) to right (-)
 *   z = dorsal (+) to ventral (-)
 *
 * After rotation, body z is NEGATED to convert to world z (depth).
 */

const PROFILES = {
  sperm: {
    headRatio: 0.33, maxWidth: 0.20, maxHeight: 0.24,
    headBulge: 1.5, tailTaper: 0.6,
    dorsalColor: '#5a6a72', ventralColor: '#a0aab0',
    dorsalHeight: 0.6, dorsalPos: 0.65,
    pectoralLen: 0.12, pectoralPos: 0.28,
    flukeSpan: 1.8, flukeLen: 0.22,
  },
  fin: {
    headRatio: 0.20, maxWidth: 0.14, maxHeight: 0.16,
    headBulge: 1.0, tailTaper: 0.7,
    dorsalColor: '#4a5a6a', ventralColor: '#c0c8d0',
    dorsalHeight: 1.0, dorsalPos: 0.60,
    pectoralLen: 0.10, pectoralPos: 0.25,
    flukeSpan: 2.0, flukeLen: 0.20,
  },
  humpback: {
    headRatio: 0.25, maxWidth: 0.22, maxHeight: 0.24,
    headBulge: 1.15, tailTaper: 0.55,
    dorsalColor: '#2d3f4f', ventralColor: '#e8e8e0',
    dorsalHeight: 0.8, dorsalPos: 0.62,
    pectoralLen: 0.28, pectoralPos: 0.27,
    flukeSpan: 2.4, flukeLen: 0.25,
  },
  blue: {
    headRatio: 0.18, maxWidth: 0.14, maxHeight: 0.16,
    headBulge: 1.05, tailTaper: 0.75,
    dorsalColor: '#3a6a9a', ventralColor: '#b0c8e0',
    dorsalHeight: 0.5, dorsalPos: 0.72,
    pectoralLen: 0.10, pectoralPos: 0.22,
    flukeSpan: 2.0, flukeLen: 0.20,
  },
  orca: {
    headRatio: 0.20, maxWidth: 0.22, maxHeight: 0.26,
    headBulge: 1.1, tailTaper: 0.6,
    dorsalColor: '#0a0a12', ventralColor: '#f0f0f0',  // black & white
    dorsalHeight: 2.0, dorsalPos: 0.50,
    pectoralLen: 0.14, pectoralPos: 0.27,
    flukeSpan: 1.8, flukeLen: 0.20,
  },
  dolphin: {
    headRatio: 0.18, maxWidth: 0.16, maxHeight: 0.18,
    headBulge: 1.05, tailTaper: 0.65,
    dorsalColor: '#607080', ventralColor: '#d0d8e0',
    dorsalHeight: 1.4, dorsalPos: 0.48,
    pectoralLen: 0.10, pectoralPos: 0.25,
    flukeSpan: 1.6, flukeLen: 0.18,
  },
}

function bodyRadius(t, profile) {
  const { headRatio, headBulge, tailTaper } = profile
  const base = Math.sin(Math.PI * t)
  const headFactor = t < headRatio
    ? 1 + (headBulge - 1) * Math.cos((t / headRatio) * Math.PI * 0.5)
    : 1
  const tailFactor = t > 0.5
    ? 1 - (1 - tailTaper) * ((t - 0.5) / 0.5) ** 1.5
    : 1
  return base * headFactor * tailFactor
}

/**
 * Interpolate between two hex colors.
 * factor 0 = colorA, factor 1 = colorB.
 */
function lerpColor(colorA, colorB, factor) {
  const a = parseInt(colorA.slice(1), 16)
  const b = parseInt(colorB.slice(1), 16)
  const ar = (a >> 16) & 0xff, ag = (a >> 8) & 0xff, ab = a & 0xff
  const br = (b >> 16) & 0xff, bg = (b >> 8) & 0xff, bb = b & 0xff
  const r = Math.round(ar + (br - ar) * factor)
  const g = Math.round(ag + (bg - ag) * factor)
  const bl = Math.round(ab + (bb - ab) * factor)
  return `rgb(${r},${g},${bl})`
}

function buildBody(profile, scale) {
  const halfLen = 0.5 * scale
  const halfW = (profile.maxWidth / 2) * scale
  const halfH = (profile.maxHeight / 2) * scale
  const rings = 16
  const slices = 14
  const vertices = []
  // Store body-frame z for each vertex (for countershading)
  const bodyZ = []

  // Body rings
  for (let i = 0; i <= rings; i++) {
    const t = i / rings
    const x = halfLen * (1 - 2 * t)
    const r = bodyRadius(t, profile)
    const ry = halfW * r
    const rz = halfH * r
    for (let j = 0; j < slices; j++) {
      const phi = (j / slices) * 2 * Math.PI
      const vz = rz * Math.sin(phi)
      vertices.push([x, ry * Math.cos(phi), vz])
      bodyZ.push(vz)
    }
  }

  const faces = []
  for (let i = 0; i < rings; i++) {
    for (let j = 0; j < slices; j++) {
      const jn = (j + 1) % slices
      const p0 = i * slices + j
      const p1 = i * slices + jn
      const p2 = (i + 1) * slices + j
      const p3 = (i + 1) * slices + jn
      faces.push([p0, p1, p3])
      faces.push([p0, p3, p2])
    }
  }

  // Fluke
  const tailX = -halfLen
  const flukeW = halfW * profile.flukeSpan
  const flukeL = halfLen * profile.flukeLen
  const fI = vertices.length
  vertices.push([tailX, 0, 0])
  vertices.push([tailX - flukeL, flukeW, 0])
  vertices.push([tailX - flukeL, -flukeW, 0])
  vertices.push([tailX - flukeL * 0.5, 0, 0])
  bodyZ.push(0, 0, 0, 0)
  faces.push([fI, fI + 1, fI + 3])
  faces.push([fI, fI + 3, fI + 1])
  faces.push([fI, fI + 3, fI + 2])
  faces.push([fI, fI + 2, fI + 3])

  // Dorsal fin (top, z+)
  if (profile.dorsalHeight > 0.1) {
    const dI = vertices.length
    const dh = halfH * profile.dorsalHeight * 1.5
    const dp = profile.dorsalPos
    const xBase1 = halfLen * (1 - 2 * (dp - 0.05))
    const xBase2 = halfLen * (1 - 2 * (dp + 0.08))
    const xPeak = halfLen * (1 - 2 * (dp + 0.02))
    const zBase = halfH * bodyRadius(dp, profile) * 0.85
    vertices.push([xBase1, 0, zBase])
    vertices.push([xBase2, 0, zBase])
    vertices.push([xPeak, 0, zBase + dh])
    bodyZ.push(zBase, zBase, zBase + dh)  // all dorsal
    faces.push([dI, dI + 1, dI + 2])
    faces.push([dI, dI + 2, dI + 1])
  }

  // Pectoral fins
  if (profile.pectoralLen > 0) {
    const pp = profile.pectoralPos
    const xFin = halfLen * (1 - 2 * pp)
    const pLen = halfLen * profile.pectoralLen
    const pW = halfW * bodyRadius(pp, profile)
    const zFin = -halfH * bodyRadius(pp, profile) * 0.3

    for (const side of [1, -1]) {
      const pI = vertices.length
      vertices.push([xFin, side * pW, zFin])
      vertices.push([xFin - pLen * 0.6, side * (pW + pLen), zFin - pLen * 0.4])
      vertices.push([xFin - pLen, side * pW, zFin - pLen * 0.1])
      bodyZ.push(zFin, zFin - pLen * 0.4, zFin - pLen * 0.1)
      faces.push([pI, pI + 1, pI + 2])
      faces.push([pI, pI + 2, pI + 1])
    }
  }

  return { vertices, faces, bodyZ }
}

/**
 * Compute per-face color based on countershading.
 * Dorsal side (body z > 0) = dark, ventral (z < 0) = light.
 * Makes roll orientation immediately visible.
 */
function computeFaceColors(faces, bodyZ, dorsalColor, ventralColor) {
  const colors = []
  // Find z range for normalization
  let zMin = Infinity, zMax = -Infinity
  for (const z of bodyZ) {
    if (z < zMin) zMin = z
    if (z > zMax) zMax = z
  }
  const zRange = zMax - zMin || 1

  const stripeHalfWidth = 0.04  // ±4% of body height around midline
  for (const [i, j, k] of faces) {
    // Average z of face vertices in body frame
    const avgZ = (bodyZ[i] + bodyZ[j] + bodyZ[k]) / 3
    // 0 = ventral (bottom), 1 = dorsal (top)
    const t = (avgZ - zMin) / zRange
    // White lateral midline stripe → roll twists it like a barber pole.
    if (Math.abs(t - 0.5) < stripeHalfWidth) {
      colors.push('rgb(245,245,245)')
      continue
    }
    // Steep sigmoid around midline → near-binary countershading.
    const k2 = 14
    const factor = 1 / (1 + Math.exp(-k2 * (t - 0.5)))
    colors.push(lerpColor(ventralColor, dorsalColor, factor))
  }
  return colors
}

/**
 * Rotate body-frame vertex to world frame.
 *
 * Order: Roll (Rx) → Pitch (Ry) → Heading (Rz)
 *
 * Conventions (matching backend compute_trajectory + animaltag PRH):
 *   heading: degrees; heading=0→+x, heading=90→-y
 *   pitch: positive = nose UP (animaltag PRH convention)
 *   roll: positive = right side down
 *
 * After rotation, body z is NEGATED to convert body z-up to world z-down (depth).
 * Net nose direction in world (z-down): (cos h cos p, -sin h cos p, -sin p),
 * matching the velocity tangent of the backend trajectory.
 */
function rotate(v, pitchDeg, rollDeg, headingDeg) {
  let [x, y, z] = v

  // Roll around X (body longitudinal axis)
  const rr = (rollDeg * Math.PI) / 180
  const cr = Math.cos(rr), sr = Math.sin(rr)
  let ny = y * cr - z * sr
  let nz = y * sr + z * cr
  y = ny; z = nz

  // Pitch around Y — positive pitch = nose up.
  // Body nose (1,0,0) → (cos p, 0, sin p); after final z-flip world_z = -sin p,
  // so positive pitch → nose toward -world_z (shallower) = nose up. Correct.
  const pr = (pitchDeg * Math.PI) / 180
  const cp = Math.cos(pr), sp = Math.sin(pr)
  let nx = x * cp - z * sp
  nz = x * sp + z * cp
  x = nx; z = nz

  // Heading around Z
  // Backend: heading_rad = -deg2rad(h), so direction = [cos(h), -sin(h)]
  // Rz(α): [1,0]→[cos(α),sin(α)]. Need [cos(h),-sin(h)] → α = -deg2rad(h)
  const hr = (-headingDeg * Math.PI) / 180
  const ch = Math.cos(hr), sh = Math.sin(hr)
  nx = x * ch - y * sh
  ny = x * sh + y * ch

  return [nx, ny, z]
}

export function buildCetaceanTrace({ species, scale, position, pitch, roll, heading }) {
  const profile = PROFILES[species]
  if (!profile) return null
  const { vertices, faces, bodyZ } = buildBody(profile, scale)
  const [px, py, pz] = position

  const faceColors = computeFaceColors(faces, bodyZ, profile.dorsalColor, profile.ventralColor)

  const xs = [], ys = [], zs = []
  for (const v of vertices) {
    const [rx, ry, rz] = rotate(v, pitch, roll, heading)
    xs.push(rx + px)
    ys.push(ry + py)
    zs.push(-rz + pz)  // NEGATE z: body z-up → world z-down (depth)
  }

  return {
    type: 'mesh3d',
    x: xs, y: ys, z: zs,
    i: faces.map((f) => f[0]),
    j: faces.map((f) => f[1]),
    k: faces.map((f) => f[2]),
    facecolor: faceColors,
    opacity: 1.0,
    flatshading: true,
    lighting: { ambient: 0.5, diffuse: 0.9, specular: 0.3, roughness: 0.6 },
    lightposition: { x: 100, y: 200, z: -100 },
    hoverinfo: 'skip',
    showlegend: false,
  }
}

export function hasModel(species) {
  return !!PROFILES[species]
}
