/**
 * Maps condition score to display color for GIS visualization.
 * Green = Good (>= 80)
 * Yellow = Moderate (60 - 79)
 * Orange = Poor (40 - 59)
 * Red = Critical (< 40)
 */
export function getRoadColor(score: number): string {
  if (score >= 80) return '#22c55e'; // Green
  if (score >= 60) return '#eab308'; // Yellow
  if (score >= 40) return '#f97316'; // Orange
  return '#ef4444'; // Red
}

export function getRoadStatusLabel(score: number): string {
  if (score >= 80) return 'Good';
  if (score >= 60) return 'Moderate';
  if (score >= 40) return 'Poor';
  return 'Critical';
}
