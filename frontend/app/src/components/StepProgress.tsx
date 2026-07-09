import AppIcon from './AppIcon'

export type StepProgressStatus = 'done' | 'active' | 'pending'

export interface StepProgressItem {
  id: string
  label: string
  status: StepProgressStatus
}

export default function StepProgress({ steps }: { steps: StepProgressItem[] }) {
  return (
    <div className="step-progress" aria-label="Setup progress">
      {steps.map((step) => (
        <div key={step.id} className={`step-progress__item step-progress__item--${step.status}`}>
          <span className={`step-dot${step.status !== 'pending' ? ` step-dot--${step.status}` : ''}`}>
            {step.status === 'done' ? <AppIcon name="check" size={10} /> : step.id.replace(/\D/g, '') || '•'}
          </span>
          <span
            className={`step-progress__label${
              step.status === 'active' ? ' step-progress__label--active' : step.status === 'done' ? ' step-progress__label--done' : ''
            }`}
          >
            {step.label}
          </span>
        </div>
      ))}
    </div>
  )
}
