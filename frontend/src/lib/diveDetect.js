const DIVE_THRESHOLD = 5 // metres — below this we consider the animal "on dive"
const BOTTOM_FRACTION = 0.8 // bottom phase = depth > 80% of dive max

export function detectDives(depth, duration) {
  if (!depth?.length) return []
  const n = depth.length
  const dt = duration / n
  const dives = []
  let inDive = false
  let startI = 0
  for (let i = 0; i < n; i++) {
    if (!inDive && depth[i] >= DIVE_THRESHOLD) {
      inDive = true
      startI = i
    } else if (inDive && depth[i] < DIVE_THRESHOLD) {
      dives.push(buildDive(depth, startI, i, dt))
      inDive = false
    }
  }
  if (inDive) dives.push(buildDive(depth, startI, n - 1, dt))
  return dives
}

function buildDive(depth, startI, endI, dt) {
  let maxD = -Infinity, maxI = startI
  for (let i = startI; i <= endI; i++) {
    if (depth[i] > maxD) { maxD = depth[i]; maxI = i }
  }
  const bottomMin = maxD * BOTTOM_FRACTION
  let bottomStart = maxI, bottomEnd = maxI
  for (let i = maxI; i >= startI; i--) {
    if (depth[i] >= bottomMin) bottomStart = i; else break
  }
  for (let i = maxI; i <= endI; i++) {
    if (depth[i] >= bottomMin) bottomEnd = i; else break
  }
  return {
    startIdx: startI,
    endIdx: endI,
    maxDepthIdx: maxI,
    maxDepth: maxD,
    startTime: startI * dt,
    endTime: endI * dt,
    duration: (endI - startI) * dt,
    bottomStart: bottomStart * dt,
    bottomEnd: bottomEnd * dt,
    bottomTime: (bottomEnd - bottomStart) * dt,
    descentRate: maxD / Math.max((maxI - startI) * dt, 0.1),
    ascentRate: maxD / Math.max((endI - maxI) * dt, 0.1),
  }
}
