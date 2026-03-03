import { useState, useEffect, useCallback, useRef } from "react";
import { Zap, Search, RefreshCw, Bookmark, FileText, Loader2 } from "lucide-react";
import { ArticleCard } from "@/components/ArticleCard";
import {
    loadSavedIds,
    saveToPersistence,
    removeFromPersistence,
    formatRelativeTime,
} from "@/lib/helpers";
import type { Article, FeedData, SourceFilter } from "@/types";

const FEED_PATH = "https://lijiyang727--ai-pulse-scraper-get-feed.modal.run";

export default function App() {
    const [articles, setArticles] = useState<Article[]>([]);
    const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
    const [activeSource, setActiveSource] = useState<SourceFilter>("all");
    const [searchQuery, setSearchQuery] = useState("");
    const [feedMeta, setFeedMeta] = useState<FeedData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [toasts, setToasts] = useState<{ id: number; icon: string; message: string }[]>([]);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const searchRef = useRef<HTMLInputElement>(null);
    const toastId = useRef(0);

    // ── Load Feed ────────────────────────
    const loadFeed = useCallback(async () => {
        try {
            setIsLoading(true);
            const resp = await fetch(FEED_PATH);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data: FeedData = await resp.json();
            setArticles(data.articles || []);
            setFeedMeta(data);
            setSavedIds(loadSavedIds());
            setIsLoading(false);
            showToast("✨", `Loaded ${data.articles.length} articles`);
        } catch (err) {
            console.error("Failed to load feed:", err);
            setIsLoading(false);
            showToast("⚠️", "Failed to load feed — run scrapers first");
        }
    }, []);

    useEffect(() => {
        loadFeed();
    }, [loadFeed]);

    // ── Keyboard shortcuts ───────────────
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "k") {
                e.preventDefault();
                searchRef.current?.focus();
            }
            if (e.key === "Escape" && document.activeElement === searchRef.current) {
                setSearchQuery("");
                searchRef.current?.blur();
            }
        };
        document.addEventListener("keydown", handler);
        return () => document.removeEventListener("keydown", handler);
    }, []);

    // ── Toast helpers ────────────────────
    const showToast = (icon: string, message: string) => {
        const id = ++toastId.current;
        setToasts((prev) => [...prev, { id, icon, message }]);
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 2500);
    };

    // ── Toggle save ──────────────────────
    const handleToggleSave = (articleId: string, source: string) => {
        setSavedIds((prev) => {
            const next = new Set(prev);
            if (next.has(articleId)) {
                next.delete(articleId);
                removeFromPersistence(articleId);
                showToast("🔖", "Article removed from saved");
            } else {
                next.add(articleId);
                saveToPersistence(articleId, source);
                showToast("⭐", "Article saved!");
            }
            return next;
        });
    };

    // ── Refresh ──────────────────────────
    const handleRefresh = async () => {
        setIsRefreshing(true);
        await loadFeed();
        setTimeout(() => setIsRefreshing(false), 600);
    };

    // ── Filtering ────────────────────────
    const filtered = articles.filter((a) => {
        if (activeSource === "saved" && !savedIds.has(a.id)) return false;
        if (activeSource !== "all" && activeSource !== "saved" && a.source !== activeSource) return false;
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            return (
                (a.title || "").toLowerCase().includes(q) ||
                (a.subtitle || "").toLowerCase().includes(q) ||
                (a.summary || "").toLowerCase().includes(q) ||
                (a.author || "").toLowerCase().includes(q)
            );
        }
        return true;
    });

    // ── Counts ───────────────────────────
    const counts = {
        all: articles.length,
        bens: articles.filter((a) => a.source === "bens_bites").length,
        rundown: articles.filter((a) => a.source === "the_rundown").length,
        saved: articles.filter((a) => savedIds.has(a.id)).length,
    };

    // ── Tab data ─────────────────────────
    const tabs: { key: SourceFilter; label: string; count: number; dot?: string; icon?: React.ReactNode }[] = [
        { key: "all", label: "All Sources", count: counts.all, dot: "bg-accent" },
        { key: "bens_bites", label: "Ben's Bites", count: counts.bens, dot: "bg-bens" },
        { key: "the_rundown", label: "The Rundown", count: counts.rundown, dot: "bg-rundown" },
        { key: "saved", label: "Saved", count: counts.saved, icon: <Bookmark className="w-3.5 h-3.5" fill="currentColor" /> },
    ];

    return (
        <div className="relative min-h-screen">
            {/* Background Effects */}
            <div className="fixed inset-0 pointer-events-none z-0 bg-mesh" />
            <div className="fixed inset-0 pointer-events-none z-0 bg-grid-overlay" />

            {/* ═══ Header ═══ */}
            <header className="sticky top-0 z-50 bg-background/92 backdrop-blur-xl border-b border-border">
                <div className="max-w-[1400px] mx-auto px-8 py-5 flex items-center gap-6 flex-wrap">
                    {/* Logo */}
                    <div className="flex items-center gap-2">
                        <div className="w-[42px] h-[42px] rounded-sm bg-accent flex items-center justify-center text-accent-foreground animate-pulse-glow">
                            <Zap className="w-6 h-6" />
                        </div>
                        <h1 className="font-heading text-[1.6rem] font-extrabold tracking-tight uppercase text-foreground">
                            AI <span className="text-accent">Pulse</span>
                        </h1>
                    </div>

                    <p className="text-text-tertiary text-sm font-mono mr-auto hidden md:block">
                        Curated AI news from the best newsletters
                    </p>

                    {/* Search */}
                    <div className="relative flex items-center">
                        <Search className="absolute left-3 w-4 h-4 text-text-muted pointer-events-none" />
                        <input
                            ref={searchRef}
                            type="text"
                            placeholder="Search articles..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="bg-white/4 border border-border rounded-sm pl-10 pr-4 py-2.5 text-foreground font-mono text-sm w-[220px] focus:w-[280px] focus:border-accent focus:shadow-[0_0_0_2px_rgba(191,245,73,0.1)] outline-none transition-all duration-200 placeholder:text-text-muted"
                        />
                    </div>

                    {/* Refresh */}
                    <button
                        onClick={handleRefresh}
                        className="flex items-center gap-2 px-5 py-2.5 bg-accent rounded-sm text-accent-foreground text-sm font-bold uppercase tracking-wider hover:bg-[#d4ff6b] active:bg-[#a8dc34] transition-all duration-150 hover:-translate-y-px"
                    >
                        <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin-fast" : ""}`} />
                        Refresh
                    </button>
                </div>
            </header>

            {/* ═══ Stats Bar ═══ */}
            <section className="max-w-[1400px] mx-auto px-8 mt-8 flex items-center justify-center gap-12 relative z-10">
                <StatItem value={String(counts.all)} label="Articles" accent />
                <div className="w-px h-9 bg-border" />
                <StatItem value="2" label="Sources" accent />
                <div className="w-px h-9 bg-border" />
                <StatItem value={String(counts.saved)} label="Saved" accent />
                <div className="w-px h-9 bg-border" />
                <StatItem
                    value={feedMeta ? formatRelativeTime(feedMeta.generatedAt) : "—"}
                    label="Last Updated"
                />
            </section>

            {/* ═══ Filter Tabs ═══ */}
            <nav className="max-w-[1400px] mx-auto px-8 mt-8 flex gap-2 flex-wrap relative z-10">
                {tabs.map((tab) => (
                    <button
                        key={tab.key}
                        onClick={() => setActiveSource(tab.key)}
                        className={`flex items-center gap-1.5 px-4 py-2 rounded-sm font-mono text-xs font-medium uppercase tracking-wider border transition-all duration-150 whitespace-nowrap ${activeSource === tab.key
                            ? "bg-accent border-accent text-accent-foreground shadow-[0_0_20px_rgba(191,245,73,0.2)]"
                            : "bg-transparent border-border text-muted-foreground hover:bg-white/4 hover:border-accent hover:text-accent"
                            }`}
                    >
                        {tab.dot && (
                            <span
                                className={`w-1.5 h-1.5 rounded-full ${activeSource === tab.key ? "bg-accent-foreground" : tab.dot
                                    }`}
                            />
                        )}
                        {tab.icon}
                        {tab.label}
                        <span
                            className={`px-1.5 py-px rounded-sm text-[0.7rem] font-bold font-mono ${activeSource === tab.key
                                ? "bg-accent-foreground/20 text-accent-foreground"
                                : "bg-white/8"
                                }`}
                        >
                            {tab.count}
                        </span>
                    </button>
                ))}
            </nav>

            {/* ═══ Main Content ═══ */}
            <main className="max-w-[1400px] mx-auto px-8 mt-8 mb-16 relative z-10 min-h-[400px]">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center gap-6 py-16 text-text-tertiary">
                        <Loader2 className="w-9 h-9 animate-spin-fast text-accent" />
                        <p className="font-mono text-sm">Loading your AI news feed...</p>
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="flex flex-col items-center justify-center gap-4 py-16 text-text-tertiary">
                        <FileText className="w-16 h-16 opacity-20" />
                        <h3 className="font-heading text-lg font-bold text-muted-foreground uppercase tracking-wide">No articles found</h3>
                        <p className="text-sm">Try changing your filter or search query</p>
                    </div>
                ) : (
                    <ul className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4">
                        {filtered.map((article, i) => (
                            <ArticleCard
                                key={article.id}
                                article={article}
                                isSaved={savedIds.has(article.id)}
                                onToggleSave={handleToggleSave}
                                index={i}
                            />
                        ))}
                    </ul>
                )}
            </main>

            {/* ═══ Toasts ═══ */}
            <div className="fixed bottom-8 right-8 flex flex-col gap-2 z-[1000] pointer-events-none">
                {toasts.map((toast) => (
                    <div
                        key={toast.id}
                        className="flex items-center gap-2 px-5 py-3 bg-accent rounded-sm text-accent-foreground font-mono text-sm font-bold uppercase tracking-wide shadow-[0_0_40px_rgba(191,245,73,0.2)] pointer-events-auto animate-toast-enter"
                    >
                        <span>{toast.icon}</span>
                        <span>{toast.message}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function StatItem({ value, label, accent }: { value: string; label: string; accent?: boolean }) {
    return (
        <div className="flex flex-col items-center gap-0.5">
            <span className={`font-heading text-2xl font-extrabold tracking-tight ${accent ? "text-accent" : "text-accent font-mono text-base"}`}>
                {value}
            </span>
            <span className="font-mono text-[0.68rem] text-text-tertiary uppercase tracking-widest font-medium">
                {label}
            </span>
        </div>
    );
}
