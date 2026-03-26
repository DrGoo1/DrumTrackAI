import React from "react";
import { EuclideanGrooveDesigner } from "../euclidean/EuclideanGrooveDesigner";
import { AudioEngine } from "../audio/AudioEngine";
import { EuclideanClickPlayer } from "../audio/EuclideanClickPlayer";
import { EuclideanPatternEvent } from "../euclidean/euclidean";
import { EUCLIDEAN_PRESETS } from "../euclidean/presets";
import { generateDrums } from "../services/api";
import type {
  DrumGenerationConfigDTO,
  EuclideanLaneConfigDTO,
} from "../types/drumGenerationConfig";

const engine = new AudioEngine();
const player = new EuclideanClickPlayer(engine);

export const EuclideanPage: React.FC = () => {
  const handlePreview = async (events: EuclideanPatternEvent[], tempo: number) => {
    await player.playPattern(events, tempo);
  };

  const handleSendToDCSM = async (events: EuclideanPatternEvent[], tempo: number) => {
    // For now, derive lane DTOs from the current preset. In a next pass,
    // we can thread current lane state up to this page if needed.
    const preset = EUCLIDEAN_PRESETS[0];
    const laneDTOs: EuclideanLaneConfigDTO[] = preset.lanes.map((lane) => ({
      instrumentId: lane.instrumentId,
      steps: lane.steps,
      hits: lane.hits,
      accents: lane.accents,
      rotate: lane.rotate,
      velocity: lane.velocity,
      accentVelocity: lane.accentVelocity,
    }));

    const bars = 4;

    const cfg: DrumGenerationConfigDTO = {
      sectionId: "euclid_section_0",
      startMeasure: 0,
      endMeasure: bars - 1,
      tempos: Array.from({ length: bars }, () => tempo),
      timeSignature: [4, 4],
      style: "Funk",
      drummer: "Purdie_AI",
      intensity: 0.7,
      variation: 0.5,
      humanize: true,
      humanizeAmount: 0.72,
      ghostNoteAmount: 0.65,
      swingAmount: 0.18,
      buildScope: "selected_section",
      fillLocations: [],
      fillType: "auto",
      generationMode: "euclidean",
      euclideanLanes: laneDTOs,
    };

    try {
      const resp = await generateDrums(cfg);
      // TODO: integrate resp.drum_track into DCSM piano roll state
      console.log("Euclidean /api/generate-drums response", resp);
    } catch (err) {
      console.error("Euclidean generateDrums failed", err);
    }
  };

  return (
    <EuclideanGrooveDesigner
      onPreviewPattern={handlePreview}
      onSendToDCSM={handleSendToDCSM}
    />
  );
};
