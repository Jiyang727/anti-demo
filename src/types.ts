export interface Article {
    id: string;
    source: "bens_bites" | "the_rundown" | "reddit";
    title: string;
    subtitle: string | null;
    author: string;
    date: string | null;
    url: string;
    summary: string | null;
    imageUrl: string | null;
    scrapedAt: string;
}

export interface FeedData {
    generatedAt: string;
    totalArticles: number;
    sources: Record<string, number>;
    articles: Article[];
}

export interface SavedArticle {
    articleId: string;
    savedAt: string;
    source: string;
}

export type SourceFilter = "all" | "bens_bites" | "the_rundown" | "saved";
