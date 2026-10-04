import type { StageState } from "@/lib/types";


interface TimelineStage {
  label: string;
  state: StageState;
  detail?: string;
}

const descriptions: Record<StageState, string> = {
  complete: "Complete",
  active: "In progress",
  pending: "Pending",
  error: "Error",
};

export function VerificationTimeline({ stages }: { stages: TimelineStage[] }) {
  return (
    <ol className="timeline" aria-label="Verification progress">
      {stages.map((stage, index) => {
        const descriptionId = `stage-${index}-description`;
        return (
          <li key={`${stage.label}-${index}`} className={`timeline-item ${stage.state}`}>
            <span className="timeline-node" aria-hidden="true" />
            <div>
              <strong aria-describedby={descriptionId}>{stage.label}</strong>
              {stage.detail && <span>{stage.detail}</span>}
              <span className="sr-only" id={descriptionId}>{descriptions[stage.state]}</span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

