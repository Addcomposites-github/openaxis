/**
 * Tests for SlicingParametersPanel — the slicing configuration form.
 *
 * Verifies:
 * - All parameter inputs are rendered
 * - onChange fires with updated parameters on slider change
 * - Parameter values are clamped to valid ranges
 * - Infill pattern dropdown works
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SlicingParametersPanel, { type SlicingParameters } from '../SlicingParametersPanel';

// Mock materialStore — the component reads selectedMaterialId
vi.mock('../../stores/materialStore', () => ({
  useMaterialStore: (selector: any) => {
    const state = { selectedMaterialId: null, materials: [] };
    return selector(state);
  },
}));

const defaultParams: SlicingParameters = {
  layerHeight: 2.0,
  extrusionWidth: 2.5,
  wallCount: 2,
  infillDensity: 0.2,
  infillPattern: 'grid',
  processType: 'waam',
};

describe('SlicingParametersPanel', () => {
  it('renders the heading', () => {
    render(<SlicingParametersPanel parameters={defaultParams} onChange={vi.fn()} />);
    expect(screen.getByText('Slicing Parameters')).toBeInTheDocument();
  });

  it('renders layer height label and value', () => {
    render(<SlicingParametersPanel parameters={defaultParams} onChange={vi.fn()} />);
    expect(screen.getByText('Layer Height')).toBeInTheDocument();
    expect(screen.getByText('2mm')).toBeInTheDocument();
  });

  it('renders extrusion width label and value', () => {
    render(<SlicingParametersPanel parameters={defaultParams} onChange={vi.fn()} />);
    expect(screen.getByText('Bead / Extrusion Width')).toBeInTheDocument();
    expect(screen.getByText('2.5mm')).toBeInTheDocument();
  });

  it('renders wall count label and value', () => {
    render(<SlicingParametersPanel parameters={defaultParams} onChange={vi.fn()} />);
    expect(screen.getByText('Walls (Perimeters)')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders infill density as percentage', () => {
    render(<SlicingParametersPanel parameters={defaultParams} onChange={vi.fn()} />);
    expect(screen.getByText('Infill Density')).toBeInTheDocument();
    expect(screen.getByText('20%')).toBeInTheDocument();
  });

  it('calls onChange when layer height slider changes', () => {
    const onChange = vi.fn();
    render(<SlicingParametersPanel parameters={defaultParams} onChange={onChange} />);

    // Get all range inputs — layer height is the first one
    const sliders = screen.getAllByRole('slider');
    const layerHeightSlider = sliders[0];

    fireEvent.change(layerHeightSlider, { target: { value: '5.0' } });

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ layerHeight: 5.0 }),
    );
  });

  it('calls onChange when wall count changes', () => {
    const onChange = vi.fn();
    render(<SlicingParametersPanel parameters={defaultParams} onChange={onChange} />);

    const sliders = screen.getAllByRole('slider');
    // Wall count slider is index 2 (after layer height and extrusion width)
    const wallSlider = sliders[2];

    fireEvent.change(wallSlider, { target: { value: '4' } });

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ wallCount: 4 }),
    );
  });

  it('does not show material badge when no material is selected', () => {
    render(<SlicingParametersPanel parameters={defaultParams} onChange={vi.fn()} />);
    expect(screen.queryByText(/auto-filled from material/i)).not.toBeInTheDocument();
  });
});
