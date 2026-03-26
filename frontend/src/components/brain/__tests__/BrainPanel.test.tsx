import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { BrainPanel } from "../BrainPanel";
import { FALLBACK_BRAIN_ELEMENTS } from "../../../types/brain";
import { useBrainPanelStore } from "../../../state/useBrainPanelStore";

jest.mock("../../../api/brain", () => {
  const { FALLBACK_BRAIN_ELEMENTS, createDefaultBrainConfig } = jest.requireActual("../../../types/brain");
  return {
    fetchBrainElements: jest.fn().mockResolvedValue(FALLBACK_BRAIN_ELEMENTS),
    fetchBrainConfig: jest.fn().mockResolvedValue(createDefaultBrainConfig(FALLBACK_BRAIN_ELEMENTS)),
    patchBrainConfig: jest.fn().mockImplementation((_sectionId: string, config: any) => Promise.resolve(config)),
  };
});

afterEach(() => {
  const definitionMap = FALLBACK_BRAIN_ELEMENTS.reduce<Record<string, (typeof FALLBACK_BRAIN_ELEMENTS)[number]>>((acc, def) => {
    acc[def.id] = def;
    return acc;
  }, {});

  useBrainPanelStore.setState((state) => ({
    ...state,
    definitions: FALLBACK_BRAIN_ELEMENTS,
    definitionMap,
    definitionsStyleKey: "__default__",
    loadingDefinitions: false,
    loadingSectionId: null,
    configs: {},
    clipboard: null,
    error: null,
  }));
});

describe("BrainPanel", () => {
  it("renders placeholder when no section is selected", () => {
    render(<BrainPanel />);
    expect(screen.getByText(/Select a section/i)).toBeInTheDocument();
  });

  it("renders element sliders when a section is provided", async () => {
    render(<BrainPanel sectionId="section-1" sectionLabel="Verse" />);
    expect(await screen.findByText(/Feel Processor/i)).toBeInTheDocument();
  });
});
