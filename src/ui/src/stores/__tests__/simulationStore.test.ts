/**
 * Tests for simulationStore — state transitions, speed control, warnings.
 *
 * Uses Zustand's vanilla API via act() to ensure synchronous state updates.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useSimulationStore } from '../simulationStore';
import type { SimulationWarning } from '../../types';

function getState() {
  return useSimulationStore.getState();
}

describe('simulationStore', () => {
  beforeEach(() => {
    // Reset to initial state before each test
    useSimulationStore.setState({
      isRunning: false,
      isPaused: false,
      currentTime: 0,
      totalTime: 300,
      speed: 1.0,
      currentLayer: 0,
      totalLayers: 50,
      collisionDetected: false,
      warnings: [],
    });
  });

  // ── Lifecycle ────────────────────────────────────────────────────────

  describe('start', () => {
    it('sets isRunning to true and resets time', () => {
      getState().setTime(100);
      getState().start();
      const s = getState();
      expect(s.isRunning).toBe(true);
      expect(s.isPaused).toBe(false);
      expect(s.currentTime).toBe(0);
    });

    it('clears existing warnings', () => {
      getState().addWarning({
        type: 'collision', message: 'test', timestamp: Date.now(), severity: 'high',
      });
      expect(getState().warnings.length).toBe(1);
      getState().start();
      expect(getState().warnings.length).toBe(0);
    });
  });

  describe('pause / resume', () => {
    it('pause sets isPaused', () => {
      getState().start();
      getState().pause();
      expect(getState().isPaused).toBe(true);
      expect(getState().isRunning).toBe(true);
    });

    it('resume clears isPaused', () => {
      getState().start();
      getState().pause();
      getState().resume();
      expect(getState().isPaused).toBe(false);
    });
  });

  describe('stop', () => {
    it('resets all running state', () => {
      getState().start();
      getState().setTime(150);
      getState().stop();
      const s = getState();
      expect(s.isRunning).toBe(false);
      expect(s.isPaused).toBe(false);
      expect(s.currentTime).toBe(0);
      expect(s.currentLayer).toBe(0);
      expect(s.collisionDetected).toBe(false);
    });
  });

  // ── Speed ────────────────────────────────────────────────────────────

  describe('setSpeed', () => {
    it('updates speed', () => {
      getState().setSpeed(2.5);
      expect(getState().speed).toBe(2.5);
    });
  });

  // ── Time / Layer sync ────────────────────────────────────────────────

  describe('setTime', () => {
    it('clamps to [0, totalTime]', () => {
      getState().setTime(-10);
      expect(getState().currentTime).toBe(0);
      getState().setTime(9999);
      expect(getState().currentTime).toBe(300);
    });

    it('updates currentLayer proportionally', () => {
      getState().setTime(150); // halfway
      expect(getState().currentLayer).toBe(25); // 50 * 0.5
    });
  });

  describe('setLayer', () => {
    it('clamps to [0, totalLayers]', () => {
      getState().setLayer(-5);
      expect(getState().currentLayer).toBe(0);
      getState().setLayer(999);
      expect(getState().currentLayer).toBe(50);
    });

    it('updates currentTime proportionally', () => {
      getState().setLayer(25); // halfway
      expect(getState().currentTime).toBe(150); // 300 * 0.5
    });
  });

  // ── Warnings ─────────────────────────────────────────────────────────

  describe('addWarning', () => {
    it('appends a warning', () => {
      const warning: SimulationWarning = {
        type: 'joint_limit', message: 'hello', timestamp: Date.now(), severity: 'low',
      };
      getState().addWarning(warning);
      expect(getState().warnings.length).toBe(1);
    });

    it('collision warning pauses and sets flag', () => {
      getState().start();
      const warning: SimulationWarning = {
        type: 'collision', message: 'oops', timestamp: Date.now(), severity: 'high',
      };
      getState().addWarning(warning);
      const s = getState();
      expect(s.collisionDetected).toBe(true);
      expect(s.isPaused).toBe(true);
    });
  });

  describe('clearWarnings', () => {
    it('empties warnings and resets collision flag', () => {
      getState().addWarning({
        type: 'collision', message: 'x', timestamp: Date.now(), severity: 'high',
      });
      getState().clearWarnings();
      const s = getState();
      expect(s.warnings.length).toBe(0);
      expect(s.collisionDetected).toBe(false);
    });
  });

  describe('dismissWarning', () => {
    it('removes a specific warning by index', () => {
      getState().addWarning({
        type: 'joint_limit', message: 'a', timestamp: 1, severity: 'low',
      });
      getState().addWarning({
        type: 'collision', message: 'b', timestamp: 2, severity: 'high',
      });
      getState().addWarning({
        type: 'workspace', message: 'c', timestamp: 3, severity: 'medium',
      });
      expect(getState().warnings.length).toBe(3);

      getState().dismissWarning(1); // remove collision
      const s = getState();
      expect(s.warnings.length).toBe(2);
      expect(s.collisionDetected).toBe(false); // no more collision warnings
    });
  });
});
