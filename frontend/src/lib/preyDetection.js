/**
 * Detect prey capture attempts from jerk data.
 * Jerk peaks above mean + 3σ with 1s refractory period.
 *
 * @param {number[]} jerk - Jerk magnitude array
 * @param {number} hz - Sampling rate (default 10 Hz for PRH)
 * @returns {number[]} Array of sample indices where prey captures detected
 */
export function detectPreyCaptures(jerk, hz = 10) {
  if (!jerk?.length) return []

  let sum = 0, sumSq = 0
  for (const v of jerk) { sum += v; sumSq += v * v }
  const mean = sum / jerk.length
  const std = Math.sqrt(Math.max(0, sumSq / jerk.length - mean * mean))
  const threshold = mean + 3 * std
  const refractory = Math.max(1, hz) // 1 second refractory

  const indices = []
  for (let i = 0; i < jerk.length; i++) {
    if (jerk[i] > threshold && (!indices.length || i - indices[indices.length - 1] > refractory)) {
      indices.push(i)
    }
  }
  return indices
}
