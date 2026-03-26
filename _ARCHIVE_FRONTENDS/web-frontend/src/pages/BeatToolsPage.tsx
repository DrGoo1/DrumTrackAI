import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Play } from "lucide-react";
import { beatTools } from "../data/beatTools";

const BeatToolsPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-black text-white pb-24">
      <header className="relative overflow-hidden px-4 pt-10 pb-14 border-b border-white/10">
        <div className="absolute inset-0" aria-hidden>
          <div className="bg-gradient-to-r from-amber-500/20 via-amber-300/10 to-transparent w-[460px] h-[460px] rounded-full blur-3xl absolute -top-32 left-[-60px]" />
          <div className="bg-gradient-to-br from-slate-900 via-black to-slate-950 absolute inset-0" />
        </div>
        <div className="relative z-10 max-w-5xl mx-auto space-y-6">
          <button
            onClick={() => navigate("/")}
            className="inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Landing
          </button>
          <div className="space-y-3">
            <p className="text-xs uppercase tracking-[0.3em] text-amber-200">Beat Tools Suite</p>
            <h1 className="text-5xl md:text-6xl font-bold gradient-text" style={{ fontFamily: "serif" }}>
              Golden Drumkit Sketchbook
            </h1>
            <p className="text-slate-200 text-lg">
              Text BeatSketch combinations, tap neon BeatPad phrases, or hum BeatSing ideas with the same gold-tier typography and feel as the main landing page.
            </p>
            <div className="inline-flex flex-wrap gap-3 text-xs uppercase tracking-[0.3em] text-slate-400">
              <span>BeatSketch Text Mode</span>
              <span>BeatPad Velocity Pads</span>
              <span>BeatSing Interpretation</span>
            </div>
          </div>
          <button
            onClick={() => navigate("/beat-prompt?surface=text")}
            className="inline-flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-amber-400 to-amber-300 text-slate-900 px-6 py-3 font-semibold shadow-xl"
          >
            Launch BeatSketch Text Mode <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </header>

      <main className="px-4 pt-12 space-y-16">
        <section className="max-w-5xl mx-auto space-y-6">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Pick a surface</p>
            <h2 className="text-3xl md:text-4xl font-bold gradient-text-gold">Capture Grooves Your Way</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {beatTools.map(({ id, label, description, accent, icon: Icon, cta }) => (
              <article
                key={id}
                className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-lg p-6 space-y-3"
              >
                <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${accent} flex items-center justify-center text-slate-900`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold">{label}</h3>
                  <p className="text-sm text-slate-300">{description}</p>
                </div>
                <button
                  onClick={() => navigate(cta)}
                  className="inline-flex items-center gap-2 text-sm text-white/80 hover:text-white"
                >
                  Open {label} <ArrowRight className="w-4 h-4" />
                </button>
              </article>
            ))}
          </div>
        </section>

        <section className="max-w-5xl mx-auto grid gap-6 md:grid-cols-2">
          <article className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-lg p-6 space-y-3">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Why Basic exists</p>
            <h3 className="text-2xl font-semibold gradient-text">Capture ideas without pressure</h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              BeatSketch Text Mode lets you type kick / snare / hat combinations, auto-apply swing, and hear Groove Preview without touching a mic. Every take can later be promoted to Advanced prompt flows or exported as MIDI.
            </p>
            <button
              onClick={() => navigate("/beat-prompt?surface=text")}
              className="inline-flex items-center gap-2 text-sm text-white/80 hover:text-white"
            >
              Try Text Mode <ArrowRight className="w-4 h-4" />
            </button>
          </article>
          <article className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-lg p-6 space-y-3">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Move up when ready</p>
            <h3 className="text-2xl font-semibold gradient-text">One click to Advanced or Pro</h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              Once your groove feels locked, convert it to an Advanced prompt for persona sculpting or jump into the Professional DCSM matrix for multi-track arranging. No exports required—the same project ID travels with you.
            </p>
            <button
              onClick={() => navigate("/#pricing")}
              className="inline-flex items-center gap-2 text-sm text-white/80 hover:text-white"
            >
              Compare tiers <ArrowRight className="w-4 h-4" />
            </button>
          </article>
        </section>

        <section className="max-w-5xl mx-auto rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900/70 to-slate-800/80 backdrop-blur-xl p-8 space-y-4 text-center">
          <Play className="w-10 h-10 text-amber-300 mx-auto" />
          <h2 className="text-3xl font-bold">Get started in under 60 seconds</h2>
          <p className="text-slate-300">
            Open Beat Tools, pick your surface, and keep everything synced to the cloud. When inspiration strikes, you should already be capturing.
          </p>
          <div className="flex flex-col md:flex-row gap-3 justify-center">
            <button
              onClick={() => navigate("/beat-tools")}
              className="inline-flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-amber-400 to-amber-300 text-slate-900 px-6 py-3 font-semibold"
            >
              Get Started Making Your Beats <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </section>
      </main>
    </div>
  );
};

export default BeatToolsPage;
