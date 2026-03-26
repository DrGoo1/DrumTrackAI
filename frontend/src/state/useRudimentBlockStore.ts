import { create } from "zustand";
import { RudimentBlock } from "../types/drumTrack";

interface RudimentBlockState {
  blocksBySection: Record<string, RudimentBlock[]>;
  setBlocksForSection: (sectionId: string, blocks: RudimentBlock[]) => void;
  clearSectionBlocks: (sectionId: string) => void;
  getBlocksForSection: (sectionId: string) => RudimentBlock[] | undefined;
}

function cloneBlocks(blocks: RudimentBlock[]): RudimentBlock[] {
  return blocks.map((block) => ({ ...block }));
}

export const useRudimentBlockStore = create<RudimentBlockState>((set, get) => ({
  blocksBySection: {},
  setBlocksForSection: (sectionId, blocks) => {
    set((state) => ({
      blocksBySection: {
        ...state.blocksBySection,
        [sectionId]: cloneBlocks(blocks),
      },
    }));
  },
  clearSectionBlocks: (sectionId) => {
    set((state) => {
      if (!state.blocksBySection[sectionId]) {
        return state;
      }
      const next = { ...state.blocksBySection };
      delete next[sectionId];
      return { blocksBySection: next };
    });
  },
  getBlocksForSection: (sectionId) => {
    const blocks = get().blocksBySection[sectionId];
    return blocks ? cloneBlocks(blocks) : undefined;
  },
}));
