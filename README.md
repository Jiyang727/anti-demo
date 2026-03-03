# AI Pulse ⚡️

AI Pulse is a beautifully designed, curated dashboard that aggregates the latest Artificial Intelligence news from top newsletters and communities. It automatically scrapes, processes, and presents AI news in a premium, mobile-responsive interface.

![Dashboard Preview](https://leno.li/favicon.svg) <!-- Replace with actual screenshot when available -->
**Live Demo:** [leno.li](https://www.leno.li)

## ✨ Features

- **Automated Daily Scraping:** Python scraper deployed on [Modal](https://modal.com) runs daily to fetch the latest news.
- **Curated Sources:** Aggregates content from industry-leading newsletters including Ben's Bites and The AI Rundown, with foundations laid for Reddit (r/artificial).
- **Premium UI/UX:** Built with React, Tailwind CSS v4, and Framer Motion for a dark-mode, glassmorphism design with silky-smooth micro-animations.
- **Mobile First:** Fully responsive design that looks stunning on every device, featuring touch-friendly scrollable tabs and optimized layouts.
- **Smart Loading:** Skeleton screens and shimmer animations provide a polished experience even while data is fetching.
- **Browser Notifications:** Opt-in notification system alerts you when fresh AI news hits the feed.
- **Local Persistence:** Your saved articles ("Bookmarks") and read state are saved securely in your browser's local storage.

## 🛠️ Technology Stack

**Frontend:**
- [React 18](https://react.dev/) + [Vite](https://vitejs.dev/)
- [TypeScript](https://www.typescriptlang.org/)
- [Tailwind CSS v4](https://tailwindcss.com/)
- [shadcn/ui](https://ui.shadcn.com/) components
- [Framer Motion](https://www.framer.com/motion/)

**Backend / Data Pipeline:**
- [Python 3.12](https://www.python.org/)
- [Modal](https://modal.com/) (Serverless compute & cron jobs)
- BeautifulSoup4 (HTML Parsing)
- Feed Storage: JSON

**Deployment:**
- Frontend hosted on [Vercel](https://vercel.com)
- Backend scraper hosted on [Modal](https://modal.com)

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Python 3.12+ (for running the scraper manually)
- [Modal account](https://modal.com) (for deploying the backend)

### Local Development (Frontend)

1. Clone the repository:
   ```bash
   git clone https://github.com/YourUsername/anti-demo.git
   cd anti-demo
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

### Running the Scraper (Backend)

The scraper is designed to run on Modal.

1. Set up a Python virtual environment and install Modal:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install modal bs4
   python3 -m modal setup
   ```

2. Run the scraper locally (executes on Modal's cloud):
   ```bash
   modal run tools/modal_scraper.py
   ```

3. Deploy the scraper as a cron job and webhook:
   ```bash
   modal deploy tools/modal_scraper.py
   ```

## 📐 Architecture (The 3-Layer Method)

This project follows a strict 3-layer separation principle defined in the project constitution (`gemini.md`):
1. **Architecture (SOPs):** Definition and rules (`gemini.md`).
2. **Navigation (Routing):** React frontend bridging raw data to user experience.
3. **Tools (Execution):** Isolated, deterministic Python scripts (`tools/`) responsible solely for data extraction.

## 📜 License

MIT License - feel free to use this as a starting point for your own intelligent news aggregators.
