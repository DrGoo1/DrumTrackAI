import React from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle,
  Crown,
  Headphones,
  Play,
  Star,
  Upload,
  Zap,
} from "lucide-react";
import { beatTools } from "../data/beatTools";

const pricingTiers = [
  {
    name: "Basic",
    price: "FREE",
    description: "Perfect for getting started",
    icon: Star,
    accent: "from-blue-500 to-blue-600",
    border: "border-blue-500",
    ctaLabel: "Get Started Free",
    cta: "/beat-tools",
    features: [
      "Simple drum arrangement",
      "Audio upload & analysis",
      "Stereo mp3 output",
      "5 tracks per month",
    ],
  },
  {
    name: "Advanced",
    price: "$19/mo",
    description: "For serious musicians",
    icon: Zap,
    accent: "from-purple-500 to-pink-500",
    border: "border-purple-500",
    badge: "POPULAR",
    ctaLabel: "Upgrade to Advanced",
    cta: "/beat-prompt",
    features: [
      "Moderate drum characteristics",
      "Arrangement modification",
      "MP3/WAV + MIDI output",
      "Limited project storage",
    ],
  },
  {
    name: "Professional",
    price: "$49/mo",
    description: "For professional studios",
    icon: Crown,
    accent: "from-yellow-500 to-orange-500",
    border: "border-yellow-500",
    ctaLabel: "Go Professional",
    cta: "/daw",
    features: [
      "Complex drum characteristics",
      "Bass integration + advanced arrangements",
      "Stereo, stems, MIDI output",
      "Extensive project storage",
    ],
  },
];

const comparisonRows = [
  {
    feature: "Custom Drum Characteristics",
    basic: "Minimal",
    advanced: "Moderate",
    professional: "Complex",
  },
  {
    feature: "Musical Style and Arrangement",
    basic: "Standard",
    advanced: "Minimal Custom",
    professional: "Fully Custom",
  },
  {
    feature: "Output",
    basic: "Stereo mp3",
    advanced: "Stereo mp3/wav + MIDI",
    professional: "Stereo, Stem, MIDI",
  },
  {
    feature: "Project Storage",
    basic: "None",
    advanced: "Limited",
    professional: "Extensive",
  },
];

const faqItems = [
  {
    question: "What makes Professional tier special?",
    answer:
      "Professional unlocks comprehensive drum characteristics, bass integration, and the full DCSM matrix for the most realistic tracks possible.",
  },
  {
    question: "How does the audio upload feature work?",
    answer:
      "Upload any audio file and DrumTracKAI analyzes tempo, feel, and style before generating a drummer-ready groove. Each tier adds more control.",
  },
  {
    question: "What file formats are supported?",
    answer:
      "We accept MP3, WAV, FLAC, and more. Outputs range from stereo renders to stems and MIDI depending on your tier.",
  },
];

const beforeAfterWave = {
  robotic: [24, 12, 30, 10, 26, 8, 32, 14, 18, 9, 22, 11],
  human: [12, 26, 16, 32, 18, 24, 20, 28, 22, 30, 18, 26],
};

const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const handleDemoNavigate = (variant: string) => {
    navigate(`/beat-sketch?mode=mic&demo=${variant}`);
  };

  return (
    <div className="min-h-screen bg-black text-white">
      <section className="relative overflow-hidden py-12">
        <div className="absolute right-0 top-1/2 -translate-y-1/2 opacity-20 z-0">
          <img src="/images/drumset-illustration.png" alt="DrumTracKAI Drumset" className="w-96 h-auto" />
        </div>
        <div className="relative z-10 max-w-7xl mx-auto px-4">
          <div className="text-center mb-8">
            <h1 className="text-6xl md:text-7xl font-bold mb-8 gradient-text" style={{ fontFamily: "serif" }}>
              DrumTracKAI
            </h1>
            <p className="text-3xl text-gray-300 mb-8 max-w-4xl mx-auto font-semibold">
              Use DrumTracKAI to create realistic drum tracks that sound like they were played by a real drummer!
            </p>
            <div className="mb-12">
              <img src="/images/DrumSet_NoBack.png" alt="DrumTracKAI Professional Drumset" className="w-[30rem] h-auto mx-auto" />
            </div>
          </div>
          <div className="text-center mb-8">
            <p className="text-4xl font-bold gradient-text-gold">Create Realistic Human Sounding Drum Tracks!</p>
          </div>
          <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 rounded-xl p-8 mb-12 max-w-4xl mx-auto">
            <div className="text-center">
              <Upload className="w-16 h-16 text-purple-400 mx-auto mb-4" />
              <h2 className="text-3xl font-bold mb-4 gradient-text">Upload Your Audio - Get Perfect Drum Tracks</h2>
              <p className="text-lg text-gray-300 mb-6">
                Simply upload any audio file and DrumTracKAI will analyze it and create a drum track that perfectly matches your music's style, tempo, and feel.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[
                  { title: "Basic", icon: Star, color: "text-blue-400", text: "Simple drum arrangement that matches your audio" },
                  { title: "Advanced", icon: Zap, color: "text-purple-400", text: "Customizable drum arrangements with modification options" },
                  { title: "Professional", icon: Crown, color: "text-yellow-400", text: "Bass integration and complex drum arrangements" },
                ].map(({ title, icon: Icon, color, text }) => (
                  <div key={title} className="bg-white/5 rounded-lg p-4">
                    <Icon className={`w-8 h-8 ${color} mx-auto mb-2`} />
                    <h3 className={`font-bold ${color} mb-2`}>{title}</h3>
                    <p className="text-sm text-gray-400">{text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="text-center mb-10">
            <button
              onClick={() => navigate("/beat-tools")}
              className="inline-flex items-center justify-center gap-2 rounded-full bg-white/90 text-slate-900 px-6 py-3 font-semibold"
            >
              Explore Beat Tools Suite <ArrowRight className="w-4 h-4" />
            </button>
          </div>
          <div className="mb-12">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold gradient-text">Hear the Difference</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
              {[
                { title: "Typical Drum Software", color: "bg-red-600 hover:bg-red-700", variant: "robotic", barColor: "bg-red-500" },
                { title: "Using DrumTracKAI", color: "bg-green-600 hover:bg-green-700", variant: "human", barColor: "bg-green-500" },
              ].map(({ title, color, variant, barColor }) => (
                <div key={title} className="bg-white/5 backdrop-blur-md rounded-xl p-6">
                  <h3 className="text-xl font-bold text-white mb-3">{title}</h3>
                  <div className="bg-gray-800 rounded-lg p-3 mb-3">
                    <div className="flex items-center gap-1 mb-2">
                      {(variant === "robotic" ? beforeAfterWave.robotic : beforeAfterWave.human).map((height, idx) => (
                        <div key={idx} className={`w-1 rounded ${barColor}`} style={{ height: `${height}px` }} />
                      ))}
                    </div>
                    <p className="text-gray-400 text-xs">{variant === "robotic" ? "Mechanical, predictable timing" : "Natural, human-like feel"}</p>
                  </div>
                  <button
                    onClick={() => handleDemoNavigate(variant)}
                    className={`w-full px-3 py-2 ${color} text-white rounded-lg transition-colors flex items-center justify-center text-sm`}
                  >
                    <Play className="mr-2 h-3 w-3" /> Play {variant === "robotic" ? "Robotic" : "DrumTracKAI"}
                  </button>
                </div>
              ))}
            </div>
          </div>
          <div className="relative mt-16 mb-16">
            <div className="max-w-7xl mx-auto px-4">
              <div className="text-left ml-0 md:ml-8">
                <p className="text-4xl md:text-6xl font-bold gradient-text whitespace-nowrap leading-tight py-2">
                  Beyond Samples, Beyond Loops, Beyond Belief!
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-12 px-4">
        <div className="max-w-3xl mx-auto text-center bg-white/5 backdrop-blur-md rounded-3xl p-8 border border-white/10">
          <div className="inline-flex items-center justify-center gap-2 text-sm text-slate-200 mb-3">
            <Headphones className="w-5 h-5" /> Neural Performance Stack
          </div>
          <h2 className="text-3xl font-bold mb-4 gradient-text">Our Neural Based Technology</h2>
          <p className="text-lg text-gray-300 mb-6">
            Advanced AI algorithms analyze and replicate the subtle timing variations that make human drumming feel natural and musical.
          </p>
          <button
            onClick={() => navigate("/bench?view=analysis")}
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg hover:from-purple-700 hover:to-blue-700 transition-colors"
          >
            Learn More About Our Technology
          </button>
        </div>
      </section>

      <section id="pricing" className="py-12 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-8 gradient-text">Choose Your Plan</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {pricingTiers.map(({ name, price, description, icon: Icon, accent, border, badge, ctaLabel, cta, features }) => (
              <div key={name} className={`bg-white/5 backdrop-blur-md rounded-xl p-6 border ${border} relative`}>
                {badge && (
                  <div className="absolute -top-2 left-1/2 -translate-x-1/2">
                    <span className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-3 py-1 rounded-full text-xs font-semibold">{badge}</span>
                  </div>
                )}
                <div className="text-center mb-6">
                  <Icon className="h-10 w-10 text-white mx-auto mb-3" />
                  <h3 className="text-xl font-bold text-white mb-2">{name}</h3>
                  <div className="text-2xl font-bold gradient-text mb-2">{price}</div>
                  <p className="text-gray-400 text-sm">{description}</p>
                </div>
                <ul className="space-y-2 mb-6 text-sm">
                  {features.map((feature) => (
                    <li key={feature} className="flex items-center text-gray-300">
                      <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => navigate(cta)}
                  className={`w-full px-4 py-2 bg-gradient-to-r ${accent} text-white rounded-lg transition-colors text-sm`}
                >
                  {ctaLabel}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-12 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-8 gradient-text">Feature Comparison</h2>
          <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-300">Feature</th>
                  <th className="text-center py-3 px-4 text-blue-400">Basic</th>
                  <th className="text-center py-3 px-4 text-purple-400">Advanced</th>
                  <th className="text-center py-3 px-4 text-yellow-400">Professional</th>
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map(({ feature, basic, advanced, professional }) => (
                  <tr key={feature} className="border-b border-gray-800">
                    <td className="py-3 px-4 text-gray-300">{feature}</td>
                    <td className="text-center py-3 px-4 text-gray-400">{basic}</td>
                    <td className="text-center py-3 px-4 text-gray-400">{advanced}</td>
                    <td className="text-center py-3 px-4 text-gray-400">{professional}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <div className="relative mb-12 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center">
            <p className="text-4xl md:text-6xl font-bold gradient-text whitespace-nowrap leading-tight py-2">
              Soul of a Drummer, Precision of AI
            </p>
          </div>
        </div>
      </div>

      <section className="py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-8 gradient-text">Frequently Asked Questions</h2>
          <div className="space-y-6">
            {faqItems.map(({ question, answer }) => (
              <div key={question} className="bg-white/5 backdrop-blur-md rounded-xl p-6">
                <h3 className="text-lg font-bold text-white mb-3">{question}</h3>
                <p className="text-gray-300">{answer}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-12 px-4">
        <div className="max-w-5xl mx-auto rounded-[40px] border border-amber-400/40 bg-gradient-to-br from-slate-900/85 via-amber-500/5 to-slate-800/75 backdrop-blur-xl p-8 text-center space-y-4 shadow-[0_25px_80px_rgba(0,0,0,0.45)]">
          <p className="text-xs uppercase tracking-[0.3em] text-amber-200">Creators & Songwriters</p>
          <h2 className="text-3xl md:text-4xl font-bold gradient-text">Ready to start with Beat Tools?</h2>
          <p className="text-slate-200">
            Text combinations in BeatSketch, tap BeatPad phrases, or hum grooves with BeatSing. When you're ready for Advanced or Professional tiers, your ideas transfer instantly.
          </p>
          <button
            onClick={() => navigate("/beat-tools")}
            className="inline-flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-amber-400 to-amber-300 text-slate-900 px-6 py-3 font-semibold shadow-lg"
          >
            Get Started Making Your Beats <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      <footer className="border-t border-white/10 px-4 py-10 text-center text-sm text-slate-400">
        <p>© {new Date().getFullYear()} DrumTracKAI • Soul of a drummer, precision of AI</p>
      </footer>

      <MobileBottomNav />
    </div>
  );
};

const MobileBottomNav: React.FC = () => {
  const navigate = useNavigate();
  return (
    <div className="md:hidden fixed bottom-4 inset-x-0 px-4">
      <div className="rounded-full border border-white/15 bg-slate-900/80 backdrop-blur-xl px-4 py-3 flex items-center justify-between text-xs text-slate-200">
        {beatTools.map(({ id, label, cta, icon: Icon }) => (
          <button key={id} onClick={() => navigate(cta)} className="flex flex-col items-center gap-1">
            <Icon className="w-4 h-4" />
            <span>{label.replace("Beat", "")}</span>
          </button>
        ))}
        <button onClick={() => navigate("/daw")} className="flex flex-col items-center gap-1 text-amber-300">
          <Crown className="w-4 h-4" />
          <span>Studio</span>
        </button>
      </div>
    </div>
  );
};

export default LandingPage;
