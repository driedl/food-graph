import { Badge } from '@ui/badge'

interface PartKindBadgeProps {
    kind: string
    className?: string
}

export function PartKindBadge({ kind, className = '' }: PartKindBadgeProps) {
    const variants = {
        plant: {
            bg: 'bg-green-100',
            text: 'text-green-700',
            border: 'border-green-200',
            icon: '🌱',
            label: 'Plant'
        },
        animal: {
            bg: 'bg-red-100',
            text: 'text-red-700',
            border: 'border-red-200',
            icon: '🐄',
            label: 'Animal'
        },
        fungus: {
            bg: 'bg-purple-100',
            text: 'text-purple-700',
            border: 'border-purple-200',
            icon: '🍄',
            label: 'Fungus'
        },
        derived: {
            bg: 'bg-blue-100',
            text: 'text-blue-700',
            border: 'border-blue-200',
            icon: '⚗️',
            label: 'Derived'
        }
    }

    const variant = variants[kind as keyof typeof variants] || {
        bg: 'bg-gray-100',
        text: 'text-gray-700',
        border: 'border-gray-200',
        icon: '❓',
        label: kind
    }

    return (
        <Badge
            variant="outline"
            className={`${variant.bg} ${variant.text} ${variant.border} text-xs font-medium ${className}`}
        >
            <span className="mr-1">{variant.icon}</span>
            {variant.label}
        </Badge>
    )
}
