/**
 * Worker identity hue derivation — anchor-spec.md §22.3, §24.7, §24.8.
 * Three validated hue slots, fixed order, never cycled: a fourth hue does not
 * clear the all-pairs colorblind-separation floor the palette was validated
 * against. Past three workers, identity is carried by direct labels
 * (already required on every segment) plus emphasis — current owner in
 * slot 1, every prior owner muted — rather than by extending the hue set.
 */

export type WorkerHueSlot = 1 | 2 | 3 | "muted";

/**
 * The hue slot is a function of *label*, not incarnation, so a worker that
 * restarts keeps its color while `label#incarnation` still reads as a
 * distinct identity in the log.
 *
 * @param label the worker's fleet-slot label (e.g. "worker-a")
 * @param claimOrder labels in the order they first claimed a segment of
 *   this run — the ordering the bars are read against
 * @param isCurrentOwner true when this label owns the segment with
 *   `ended_at === null`
 */
export function workerHueSlot(
  label: string,
  claimOrder: string[],
  isCurrentOwner: boolean,
): WorkerHueSlot {
  const index = claimOrder.indexOf(label);
  if (claimOrder.length <= 3) {
    return index === 0 ? 1 : index === 1 ? 2 : 3;
  }
  // Beyond three distinct labels: color by emphasis, not by extending the hue
  // set — the current owner gets slot 1, every prior owner is muted.
  return isCurrentOwner ? 1 : "muted";
}

export function hueSlotVar(slot: WorkerHueSlot): string {
  if (slot === "muted") return "var(--ink-muted)";
  return `var(--worker-${slot})`;
}

export function hueSlotClassName(slot: WorkerHueSlot): string {
  if (slot === "muted") return "text-ink-muted";
  return `text-worker-${slot}`;
}
