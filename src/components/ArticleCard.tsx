import { GlowingEffect } from "@/components/ui/glowing-effect";
import { formatDate, getSourceLabel } from "@/lib/helpers";
import { Bookmark, ExternalLink, FileText } from "lucide-react";
import type { Article } from "@/types";

interface ArticleCardProps {
    article: Article;
    isSaved: boolean;
    onToggleSave: (id: string) => void;
    index: number;
}

export function ArticleCard({ article, isSaved, onToggleSave, index }: ArticleCardProps) {
    const sourceLabel = getSourceLabel(article.source);
    const dateStr = formatDate(article.date);
    const delay = Math.min(index * 0.05, 0.5);

    const badgeColors: Record<string, string> = {
        bens_bites: "bg-accent/12 text-bens border border-bens/25",
        the_rundown: "bg-rundown/10 text-rundown border border-rundown/20",
        reddit: "bg-reddit/10 text-reddit border border-reddit/20",
    };

    return (
        <li
            className="list-none animate-card-enter"
            style={{ animationDelay: `${delay}s` }}
        >
            {/* Outer wrapper with GlowingEffect */}
            <div className="relative h-full rounded-sm border-[0.75px] border-border p-[3px]">
                <GlowingEffect
                    spread={40}
                    glow
                    disabled={false}
                    proximity={64}
                    inactiveZone={0.01}
                    borderWidth={2}
                />

                {/* Inner card */}
                <div
                    className="relative flex h-full flex-col overflow-hidden rounded-sm bg-card cursor-pointer transition-colors duration-200 hover:bg-card-hover"
                    onClick={() => window.open(article.url, "_blank", "noopener")}
                >
                    {/* Image */}
                    <div className="relative h-[140px] sm:h-[180px] overflow-hidden bg-muted card-image-gradient">
                        {article.imageUrl ? (
                            <img
                                src={article.imageUrl}
                                alt=""
                                loading="lazy"
                                className="w-full h-full object-cover transition-transform duration-300 hover:scale-[1.04]"
                                onError={(e) => {
                                    const target = e.target as HTMLImageElement;
                                    target.style.display = "none";
                                    target.parentElement!.classList.add("flex", "items-center", "justify-center");
                                    const icon = document.createElement("div");
                                    icon.innerHTML = '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" class="opacity-10 text-accent"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>';
                                    target.parentElement!.appendChild(icon);
                                }}
                            />
                        ) : (
                            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[#141414] to-[#1a1a1a]">
                                <FileText className="w-10 h-10 opacity-10 text-accent" />
                            </div>
                        )}
                    </div>

                    {/* Body */}
                    <div className="flex flex-col gap-2 p-5 sm:p-6 flex-1">
                        {/* Meta */}
                        <div className="flex items-center justify-between gap-2">
                            <span
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-sm font-mono text-[0.65rem] font-bold uppercase tracking-wider ${badgeColors[article.source] ?? ""}`}
                            >
                                {sourceLabel}
                            </span>
                            <span className="font-mono text-[0.72rem] text-text-tertiary">
                                {dateStr}
                            </span>
                        </div>

                        {/* Title */}
                        <h2 className="font-heading text-base sm:text-[1.1rem] font-bold leading-tight line-clamp-2 tracking-tight text-foreground">
                            {article.title}
                        </h2>

                        {/* Subtitle */}
                        {article.subtitle && (
                            <p className="text-sm text-muted-foreground line-clamp-2 leading-snug">
                                {article.subtitle}
                            </p>
                        )}

                        {/* Summary */}
                        {article.summary && (
                            <p className="text-xs text-text-tertiary line-clamp-3 leading-relaxed">
                                {article.summary}
                            </p>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between px-5 sm:px-6 pb-5 pt-1">
                        <span className="font-mono text-[0.72rem] text-text-tertiary font-medium truncate max-w-[50%]">
                            {article.author || "Unknown"}
                        </span>
                        <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                            <button
                                onClick={() => onToggleSave(article.id)}
                                className={`group relative flex items-center justify-center w-8 h-8 rounded-sm border transition-all duration-150 ${isSaved
                                    ? "bg-accent border-accent text-accent-foreground hover:bg-[#d4ff6b]"
                                    : "bg-transparent border-border text-text-tertiary hover:bg-accent-dim hover:border-accent hover:text-accent"
                                    }`}
                                aria-label={isSaved ? "Unsave article" : "Save article"}
                            >
                                <Bookmark className="w-4 h-4" fill={isSaved ? "currentColor" : "none"} />
                                <span className="tooltip">{isSaved ? "Unsave" : "Save"}</span>
                            </button>
                            <a
                                href={article.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="group relative flex items-center justify-center w-8 h-8 rounded-sm border border-border bg-transparent text-text-tertiary hover:bg-accent-dim hover:border-accent hover:text-accent transition-all duration-150"
                                aria-label="Open in new tab"
                            >
                                <ExternalLink className="w-4 h-4" />
                                <span className="tooltip">Open</span>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </li>
    );
}
