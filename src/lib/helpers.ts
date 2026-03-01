import type { SavedArticle } from "@/types";

const STORAGE_KEY = "ai-pulse-saved";

export function loadSavedIds(): Set<string> {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
            const parsed: SavedArticle[] = JSON.parse(raw);
            return new Set(parsed.map((s) => s.articleId));
        }
    } catch (e) {
        console.warn("Failed to load saved articles:", e);
    }
    return new Set();
}

export function saveToPersistence(articleId: string, source: string) {
    const list = getSavedList();
    if (!list.find((s) => s.articleId === articleId)) {
        list.push({ articleId, savedAt: new Date().toISOString(), source });
        localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    }
}

export function removeFromPersistence(articleId: string) {
    const list = getSavedList().filter((s) => s.articleId !== articleId);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
}

function getSavedList(): SavedArticle[] {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    } catch {
        return [];
    }
}

export function formatDate(dateStr: string | null): string {
    if (!dateStr) return "Unknown";
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return "Unknown";
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffH = Math.floor(diffMs / (1000 * 60 * 60));
        const diffD = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        if (diffH < 1) return "Just now";
        if (diffH < 24) return `${diffH}h ago`;
        if (diffD < 7) return `${diffD}d ago`;
        return date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
        });
    } catch {
        return "Unknown";
    }
}

export function formatRelativeTime(isoStr: string): string {
    try {
        const date = new Date(isoStr);
        const diffMin = Math.floor((Date.now() - date.getTime()) / (1000 * 60));
        if (diffMin < 1) return "Just now";
        if (diffMin < 60) return `${diffMin}m ago`;
        const diffH = Math.floor(diffMin / 60);
        if (diffH < 24) return `${diffH}h ago`;
        return `${Math.floor(diffH / 24)}d ago`;
    } catch {
        return "—";
    }
}

export function getSourceLabel(source: string): string {
    const labels: Record<string, string> = {
        bens_bites: "Ben's Bites",
        the_rundown: "The Rundown",
        reddit: "Reddit",
    };
    return labels[source] || source;
}
