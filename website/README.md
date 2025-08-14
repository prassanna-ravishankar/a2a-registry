# A2A Registry Website

Modern React-based website for the A2A Registry, featuring real-time search, filtering, and a beautiful UI.

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev
# Visit http://localhost:5173

# Build for production (outputs to ../docs)
npm run build
```

## How It Works

1. **Data Source**: Reads from `/registry.json` (generated from agent files)
2. **Build Output**: Builds to `../docs` folder for GitHub Pages
3. **CI/CD**: GitHub Actions automatically builds on push to main

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Lucide React** - Icons

## Features

- 🔍 Real-time search
- 🏷️ Tag-based filtering
- 📊 Live statistics
- 📱 Fully responsive
- ⚡ Fast and modern
- 🎨 Beautiful gradients

## File Structure

```
website/
├── src/
│   ├── App.jsx         # Main React component
│   ├── main.jsx        # Entry point
│   └── index.css       # Tailwind CSS
├── public/
│   └── logo.svg        # Site logo
├── index.html          # HTML template
├── package.json        # Dependencies
├── vite.config.js      # Build config
└── tailwind.config.js  # Tailwind config
```

## Deployment

The website is automatically built and deployed via GitHub Actions when:
- New agents are added
- Website code is updated
- Manually triggered

The build process:
1. Generates fresh `registry.json` from agent files
2. Builds the React app
3. Deploys to GitHub Pages