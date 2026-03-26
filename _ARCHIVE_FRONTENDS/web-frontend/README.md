# DrumTracKAI 3-Tier Frontend System
## Professional React-based Interface for AI Drum Analysis

### [TARGET] Overview
This comprehensive 3-tier frontend system showcases DrumTracKAI's advanced AI capabilities, from basic pattern recognition to expert-level signature song analysis with MVSep stem separation.

###  Architecture

#### **3-Tier System:**
- **Basic Tier** - 65% AI Sophistication, Essential Analysis
- **Professional Tier** - 82% AI Sophistication, Advanced Features  
- **Expert Tier** - 88.7% AI Sophistication, MVSep Integration

### [FOLDER] Project Structure
```
web-frontend/
 src/
    App.js                    # Main application with navigation
    App.css                   # Comprehensive styling system
    index.js                  # React entry point
    index.css                 # Base styles with Tailwind
    pages/
        LandingPage.js        # Hero landing with live demos
        TierComparison.js     # Detailed pricing comparison
        BasicTier.js          # Basic tier interface
        ProfessionalTier.js   # Professional tier interface
        ExpertTier.js         # Expert tier interface
 package.json                  # Dependencies and scripts
 tailwind.config.js           # Custom styling configuration
 README.md                    # This file
```

### [LAUNCH] Quick Start

#### **Prerequisites:**
- Node.js 16+ and npm
- Modern web browser
- DrumTracKAI backend running (for full functionality)

#### **Installation:**
```bash
# Navigate to frontend directory
cd web-frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build
```

#### **Development Server:**
- Runs on `http://localhost:3000`
- Hot reload enabled
- Responsive design testing available

### Current Landing Experience (v1.1.17)
- `/` now serves the unified marketing landing built directly inside `web-frontend/src/pages/LandingPage.tsx`.
- BeatSketch, BeatPad, and BeatSing are represented as Basic-tier cards that deep-link to `/beat-sketch?mode=mic|pads|sing` for seamless hand-off.
- Pricing tiles highlight **Basic (Free)**, **Advanced**, and **Professional** tiers, each routing to the appropriate React route (`/beat-sketch`, `/beat-prompt`, `/daw`).
- Professional workflows are grouped into cards that jump to `Audio Upload & Analysis` (`/beat-sketch?mode=upload`), `Traditional Drum Builder` (`/daw`), and `Euclidean Creation` (`/euclidean`).
- A lightweight mobile micro-site layout (swipeable cards + sticky bottom nav) keeps the color/font scheme consistent for Instagram/TikTok in-app browsers while exposing share actions.

#### Landing Navigation Map
| UI Surface | Target Route | Scroll Anchor |
| --- | --- | --- |
| Top nav “Beat Tools” | `/#beat-tools` | `beat-tools` section |
| Top nav “Pricing” | `/#pricing` | `pricing` section |
| Top nav “Workflows” | `/#pro-workflows` | `pro-workflows` section |
| Hero CTA “Start BeatSketch” | `/beat-sketch?mode=mic` | n/a |
| Hero CTA “Try Beat Prompt” | `/beat-prompt` | n/a |
| Beat Tools cards | `/beat-sketch?mode=mic|pads|sing` | n/a |
| Pricing tiles | `/beat-sketch`, `/beat-prompt`, `/daw` | n/a |
| Pro Workflow cards | `/beat-sketch?mode=upload`, `/daw`, `/euclidean` | `pro-workflows` section |
| Mobile sticky nav buttons | `/beat-sketch?mode=mic|pads|sing`, `/daw` | n/a |

Hash-based nav items (`/#beat-tools`, `/#pricing`, `/#pro-workflows`) rely on a small `useEffect` inside `LandingPage` that calls `scrollIntoView({ behavior: "smooth" })` once the hero mounts, ensuring SPA routing stays instant while anchors remain accessible from every route.

### [ART] Features

#### **Landing Page:**
- **Hero Section** with live signature song demos
- **Statistics Showcase** (88.7% sophistication, 5,650+ training files)
- **Feature Highlights** (Expert AI, MVSep, Signature Songs)
- **Interactive Tier Previews** with clear upgrade paths

#### **Tier Comparison:**
- **Detailed Feature Matrix** comparing all capabilities
- **Visual Sophistication Indicators** for each tier
- **FAQ Section** addressing common questions
- **Pricing Information** with upgrade flows

#### **Basic Tier ($9.99/month):**
- Single file upload (WAV, MP3, 50MB limit)
- 10 analyses per month with usage tracking
- Essential pattern recognition and tempo detection
- Sample tracks for learning
- Quick recording (30-second limit)

#### **Professional Tier ($29.99/month):**
- Batch processing (up to 50 files)
- Real-time monitoring with progress tracking
- Advanced pattern analysis and style comparison
- Classic beats database access (40 tracks)
- Export capabilities and API access

#### **Expert Tier ($79.99/month):**
- Unlimited processing with no file size limits
- MVSep stem separation (HDemucs + DrumSep)
- Full signature song database access
- Custom model training capabilities
- White-label solutions and dedicated support

### [AUDIO] Key Technologies

#### **Frontend Stack:**
- **React 18.2.0** - Modern component-based architecture
- **TailwindCSS 3.3.0** - Utility-first styling with custom themes
- **Lucide React** - Consistent icon system
- **Recharts** - Data visualization for analysis results

#### **Styling Features:**
- **Glass Morphism Effects** with backdrop blur
- **Tier-Specific Color Schemes** (Blue, Purple, Gold)
- **Smooth Animations** and micro-interactions
- **Responsive Design** for all device sizes
- **Custom Progress Indicators** and loading states

### [LINK] Backend Integration

#### **API Endpoints Expected:**
```javascript
// File upload handling
POST /api/upload
Content-Type: multipart/form-data

// Analysis initiation
POST /api/analyze
{
  "fileId": "string",
  "analysisType": "basic|advanced|expert|signature",
  "tier": "basic|professional|expert"
}

// Real-time progress updates
GET /api/progress/:jobId
{
  "progress": 0-100,
  "status": "processing|completed|failed",
  "currentStep": "string"
}

// Analysis results retrieval
GET /api/results/:jobId
{
  "sophistication": "percentage",
  "accuracy": "percentage",
  "tempo": "BPM",
  "patterns": ["array"],
  "confidence": "percentage"
}

// User usage tracking
GET /api/user/usage
{
  "tier": "basic|professional|expert",
  "monthlyUsage": number,
  "limit": number
}
```

#### **File Upload Specifications:**
- **Basic Tier:** WAV, MP3 up to 50MB
- **Professional Tier:** WAV, MP3, FLAC, M4A up to 200MB
- **Expert Tier:** All formats, unlimited size

### [ART] Customization

#### **Tier Colors:**
```css
:root {
  --tier-basic: #3b82f6;      /* Blue */
  --tier-professional: #8b5cf6; /* Purple */
  --tier-expert: #f59e0b;      /* Gold */
}
```

#### **Animation System:**
- Fade-in animations for page transitions
- Progress bar animations with tier-specific colors
- Hover effects for interactive elements
- Loading spinners and state indicators

### [MOBILE] Responsive Design

#### **Breakpoints:**
- **Mobile:** < 768px - Stacked layouts, simplified navigation
- **Tablet:** 768px - 1024px - Adaptive grid systems
- **Desktop:** > 1024px - Full feature layouts

#### **Mobile Optimizations:**
- Touch-friendly upload areas
- Simplified tier comparison tables
- Collapsible navigation menus
- Optimized file upload flows

### [CONFIG] Development

#### **Available Scripts:**
```bash
npm start          # Development server with hot reload
npm run build      # Production build
npm test           # Run test suite
npm run eject      # Eject from Create React App
```

#### **Environment Variables:**
```bash
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_UPLOAD_MAX_SIZE=52428800  # 50MB for basic tier
REACT_APP_ENABLE_DEMO_MODE=true     # Enable demo features
```

### [LAUNCH] Deployment

#### **Production Build:**
```bash
# Build optimized production files
npm run build

# Files generated in build/ directory
# Deploy build/ contents to web server
```

#### **Unified Landing Deployment Options**

| Option | When to choose it | Steps |
| --- | --- | --- |
| **S3 + CloudFront (static SPA)** | Primary production path when DrumTracKAI API lives on AWS | 1) `npm run build` → upload `build/` to versioned `s3://drumtrackai-frontend-prod/<commit>/`. 2) Update CloudFront origin to new S3 key. 3) Invalidate `/*` so `/`, `/#beat-tools`, `/beat-sketch` etc. pull the latest bundle. |
| **Vercel / Netlify (edge)** | Fast preview URLs + marketing tests | 1) Connect repo. 2) Configure build command `npm run build`, output `build`. 3) Set `REACT_APP_API_URL` + `PUBLIC_URL=https://<preview>.vercel.app`. 4) Enable SPA fallback so BeatSketch/Prompt routes resolve. |
| **Docker + Nginx** | Need parity with backend release or on-prem installs | 1) Copy `build/` into `/usr/share/nginx/html`. 2) Bake an image using `web-frontend/Dockerfile` (or extend backend Docker). 3) Configure Nginx with `try_files $uri /index.html` so hash routes and `/beat-sketch?mode=` remain client-side. |
| **Windows/IIS drop** | Internal demos where Ops prefers Windows servers | 1) Zip `build/`, unpack to IIS site root. 2) Add `web.config` rewrite rule to send unmatched paths to `index.html`. 3) Ensure MIME types for `.webmanifest`, `.woff2`, `.mjs` exist. |

##### Docker Compose (backend + frontend bundle)
The repo ships with `docker-compose.yml`, `web-frontend/Dockerfile`, and `web-frontend/nginx.conf` so you can run landing + BeatSketch + backend locally or in staging as a single stack.

1. `docker compose build frontend backend` — invokes the Node builder, bakes the React bundle, and copies it into the Nginx runtime image. Optional overrides: `docker compose build frontend --build-arg REACT_APP_API_BASE=https://api.dev.drumtrack.ai` (or use `REACT_APP_API_URL`).
2. `docker compose up -d` — exposes the frontend on `http://localhost:3000` and backend on `http://localhost:8000`.
3. All browser requests to `/api/*` hit the frontend container first; Nginx forwards them to the `backend` service (`proxy_pass http://backend:8000`). Because of this, the SPA can default `API_BASE` to `window.location.origin`, keeping env-specific URLs out of the bundle.
4. When promoting to prod with Docker, push both images to your registry (tagged `drumtrackai-frontend:v1.1.17`, `drumtrackai-backend:v1.1.17`), then deploy the compose stack or equivalent orchestrator spec.

Tip: when serving strictly behind the Docker Nginx proxy, you no longer need to expose backend port 8000 publicly—frontend handles proxying and CORS alignment.

**Environment keys**

| Variable | Purpose | Default |
| --- | --- | --- |
| `REACT_APP_API_URL` | Points BeatSketch/Prompt/DCSM calls to the correct backend cluster | `http://localhost:8000/api` during dev |
| `PUBLIC_URL` | Needed when serving the SPA from a sub-path (e.g., `/drums/`) so hash scrolling still resolves | empty → root |
| `REACT_APP_ENABLE_DEMO_MODE` | Enables local demo assets for mobile playback buttons | `true` |

**Release checklist**
1. Run `npm run build` and confirm `build/index.html` references hashed assets only.
2. Smoke the bundle locally (`npx serve -s build`) and test `/`, `/beat-sketch?mode=mic`, `/beat-prompt`, `/daw`, `/euclidean`.
3. Validate hash scrolling after deploy (`/#beat-tools`, `/#pricing`, `/#pro-workflows`).
4. Verify share buttons on mobile previews still resolve the canonical production URL (update `PUBLIC_URL` if it changes).
5. Coordinate with backend release to ensure CORS + `REACT_APP_API_URL` target the same environment (dev, staging, prod).

#### **Performance Optimizations:**
- Code splitting for tier-specific components
- Lazy loading for analysis results
- Image optimization for tier badges
- Bundle size optimization with tree shaking

### [TEST] Testing

#### **Component Testing:**
```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Generate coverage report
npm test -- --coverage
```

#### **Manual Testing Checklist:**
- [ ] Landing page loads with live demos
- [ ] Tier comparison table displays correctly
- [ ] File upload works for each tier
- [ ] Progress tracking updates in real-time
- [ ] Results display properly formatted
- [ ] Mobile responsive design functions
- [ ] Upgrade flows work between tiers

### [BAR_CHART] Analytics Integration

#### **Tracking Events:**
- Tier selection and upgrades
- File upload attempts and successes
- Analysis completion rates
- Feature usage by tier
- User engagement metrics

### [LOCKED] Security Considerations

#### **File Upload Security:**
- File type validation on frontend and backend
- Size limits enforced per tier
- Malware scanning integration points
- Secure file storage and cleanup

#### **User Data Protection:**
- No sensitive data stored in frontend
- Secure API communication (HTTPS)
- User session management
- Privacy-compliant analytics

### [AUDIO] Integration with DrumTracKAI Backend

#### **Expected Backend Services:**
- **Expert Model API** - 88.7% sophistication analysis
- **MVSep Service** - HDemucs + DrumSep stem separation
- **Signature Song Database** - Porcaro, Peart, Copeland tracks
- **Real-time Monitor** - Live progress tracking
- **User Management** - Tier-based access control

### [TRENDING_UP] Future Enhancements

#### **Planned Features:**
- Real-time collaboration tools
- Advanced visualization components
- Mobile app integration
- API documentation portal
- White-label customization options

### 🤝 Contributing

#### **Development Workflow:**
1. Fork the repository
2. Create feature branch
3. Implement changes with tests
4. Submit pull request
5. Code review and merge

#### **Code Standards:**
- ESLint configuration for consistent code style
- Prettier for automatic formatting
- Component documentation with PropTypes
- Accessibility compliance (WCAG 2.1)

### [CALL] Support

For technical support or questions:
- Check the FAQ section in tier comparison
- Review API documentation
- Contact development team
- Submit issues via GitHub

---

**DrumTracKAI 3-Tier Frontend** - Professional AI-powered drum analysis interface showcasing 88.7% sophistication Expert model with MVSep integration.

*Built with React, TailwindCSS, and modern web technologies for optimal user experience.*
