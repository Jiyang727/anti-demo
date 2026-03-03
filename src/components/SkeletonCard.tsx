import { GlowingEffect } from "@/components/ui/glowing-effect";

export function SkeletonCard() {
    return (
        <li className="list-none">
            <div className="relative h-full rounded-sm border-[0.75px] border-border p-[3px]">
                <GlowingEffect
                    spread={40}
                    glow
                    disabled
                    proximity={64}
                    inactiveZone={0.01}
                    borderWidth={2}
                />
                <div className="relative flex h-full flex-col overflow-hidden rounded-sm bg-card">
                    {/* Image placeholder */}
                    <div className="h-[140px] sm:h-[180px] bg-muted animate-skeleton-shimmer" />

                    {/* Body */}
                    <div className="flex flex-col gap-3 p-5 sm:p-6 flex-1">
                        {/* Badge + date */}
                        <div className="flex items-center justify-between gap-2">
                            <div className="h-4 w-20 rounded-sm bg-white/5 animate-skeleton-shimmer" />
                            <div className="h-3 w-14 rounded-sm bg-white/5 animate-skeleton-shimmer" style={{ animationDelay: "0.1s" }} />
                        </div>

                        {/* Title */}
                        <div className="space-y-2">
                            <div className="h-5 w-full rounded-sm bg-white/5 animate-skeleton-shimmer" style={{ animationDelay: "0.15s" }} />
                            <div className="h-5 w-3/4 rounded-sm bg-white/5 animate-skeleton-shimmer" style={{ animationDelay: "0.2s" }} />
                        </div>

                        {/* Summary */}
                        <div className="space-y-1.5 mt-1">
                            <div className="h-3 w-full rounded-sm bg-white/4 animate-skeleton-shimmer" style={{ animationDelay: "0.25s" }} />
                            <div className="h-3 w-5/6 rounded-sm bg-white/4 animate-skeleton-shimmer" style={{ animationDelay: "0.3s" }} />
                            <div className="h-3 w-2/3 rounded-sm bg-white/4 animate-skeleton-shimmer" style={{ animationDelay: "0.35s" }} />
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between px-5 sm:px-6 pb-5 pt-1">
                        <div className="h-3 w-24 rounded-sm bg-white/5 animate-skeleton-shimmer" style={{ animationDelay: "0.4s" }} />
                        <div className="flex gap-2">
                            <div className="w-8 h-8 rounded-sm bg-white/4 animate-skeleton-shimmer" style={{ animationDelay: "0.45s" }} />
                            <div className="w-8 h-8 rounded-sm bg-white/4 animate-skeleton-shimmer" style={{ animationDelay: "0.5s" }} />
                        </div>
                    </div>
                </div>
            </div>
        </li>
    );
}
