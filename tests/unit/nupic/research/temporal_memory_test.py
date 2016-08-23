#!/usr/bin/env python
# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2014-2016, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero Public License for more details.
#
# You should have received a copy of the GNU Affero Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

import tempfile
import unittest
import copy

from nupic.data.generators.pattern_machine import PatternMachine
from nupic.data.generators.sequence_machine import SequenceMachine
from nupic.research.temporal_memory import TemporalMemory

try:
  import capnp
except ImportError:
  capnp = None
if capnp:
  from nupic.proto import TemporalMemoryProto_capnp



class TemporalMemoryTest(unittest.TestCase):

  def testInitInvalidParams(self):
    # Invalid columnDimensions
    kwargs = {"columnDimensions": [], "cellsPerColumn": 32}
    self.assertRaises(ValueError, TemporalMemory, **kwargs)

    # Invalid cellsPerColumn
    kwargs = {"columnDimensions": [2048], "cellsPerColumn": 0}
    self.assertRaises(ValueError, TemporalMemory, **kwargs)
    kwargs = {"columnDimensions": [2048], "cellsPerColumn": -10}
    self.assertRaises(ValueError, TemporalMemory, **kwargs)


  def testActivateCorrectlyPredictiveCells(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.5,
      minThreshold=2,
      maxNewSynapseCount=3,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.0,
      seed=42)

    previousActiveColumns = [0]
    activeColumns = [1]
    previousActiveCells = [0,1,2,3]
    expectedActiveCells = [4]

    activeSegment = tm.connections.createSegment(expectedActiveCells[0])
    tm.connections.createSynapse(activeSegment, previousActiveCells[0], .5)
    tm.connections.createSynapse(activeSegment, previousActiveCells[1], .5)
    tm.connections.createSynapse(activeSegment, previousActiveCells[2], .5)
    tm.connections.createSynapse(activeSegment, previousActiveCells[3], .5)

    tm.compute(previousActiveColumns, True)
    self.assertEqual(expectedActiveCells, tm.getPredictiveCells())
    tm.compute(activeColumns, True)
    self.assertEqual(expectedActiveCells, tm.getActiveCells())


  def testBurstUnpredictedColumns(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.5,
      minThreshold=2,
      maxNewSynapseCount=3,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.0,
      seed=42)

    activeColumns = [0]
    burstingCells = [0, 1, 2, 3]

    tm.compute(activeColumns, True)

    self.assertEqual(burstingCells, tm.getActiveCells())


  def testZeroActiveColumns(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.5,
      minThreshold=2,
      maxNewSynapseCount=3,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.0,
      seed=42)

    previousActiveColumns = [0]
    previousActiveCells = [0, 1, 2, 3]
    expectedActiveCells = [4]

    segment = tm.connections.createSegment(expectedActiveCells[0])
    tm.connections.createSynapse(segment, previousActiveCells[0], .5)
    tm.connections.createSynapse(segment, previousActiveCells[1], .5)
    tm.connections.createSynapse(segment, previousActiveCells[2], .5)
    tm.connections.createSynapse(segment, previousActiveCells[3], .5)

    tm.compute(previousActiveColumns, True)
    self.assertFalse(len(tm.getActiveCells()) == 0)
    self.assertFalse(len(tm.getWinnerCells()) == 0)
    self.assertFalse(len(tm.getPredictiveCells()) == 0)

    zeroColumns = []
    tm.compute(zeroColumns, True)

    self.assertTrue(len(tm.getActiveCells()) == 0)
    self.assertTrue(len(tm.getWinnerCells()) == 0)
    self.assertTrue(len(tm.getPredictiveCells()) == 0)


  def testPredictedActiveCellsAreAlwaysWinners(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.5,
      minThreshold=2,
      maxNewSynapseCount=3,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.0,
      seed=42)

    previousActiveColumns = [0]
    activeColumns = [1]
    previousActiveCells = [0, 1, 2, 3]
    expectedWinnerCells = [4, 6]

    activeSegment1 = tm.connections.createSegment(expectedWinnerCells[0])
    tm.connections.createSynapse(activeSegment1, previousActiveCells[0], .5)
    tm.connections.createSynapse(activeSegment1, previousActiveCells[1], .5)
    tm.connections.createSynapse(activeSegment1, previousActiveCells[2], .5)

    activeSegment2 = tm.connections.createSegment(expectedWinnerCells[1])
    tm.connections.createSynapse(activeSegment2, previousActiveCells[0], .5)
    tm.connections.createSynapse(activeSegment2, previousActiveCells[1], .5)
    tm.connections.createSynapse(activeSegment2, previousActiveCells[2], .5)

    tm.compute(previousActiveColumns, False)
    tm.compute(activeColumns, False)

    self.assertEqual(expectedWinnerCells, tm.getWinnerCells())


  def testReinforceCorrectlyActiveSegments(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.2,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=4,
      permanenceIncrement=.10,
      permanenceDecrement=.08,
      predictedSegmentDecrement=0.02,
      seed=42)

    prevActiveColumns = [0]
    prevActiveCells = [0,1,2,3]
    activeColumns = [1]
    activeCell = 5

    activeSegment = tm.connections.createSegment(activeCell)
    as1 = tm.connections.createSynapse(activeSegment, prevActiveCells[0], .5)
    as2 = tm.connections.createSynapse(activeSegment, prevActiveCells[1], .5)
    as3 = tm.connections.createSynapse(activeSegment, prevActiveCells[2], .5)
    is1 = tm.connections.createSynapse(activeSegment, 81, .5) #inactive synapse

    tm.compute(prevActiveColumns, True)
    tm.compute(activeColumns, True)

    self.assertAlmostEqual(.6, tm.connections.dataForSynapse(as1).permanence)
    self.assertAlmostEqual(.6, tm.connections.dataForSynapse(as2).permanence)
    self.assertAlmostEqual(.6, tm.connections.dataForSynapse(as3).permanence)
    self.assertAlmostEqual(.42, tm.connections.dataForSynapse(is1).permanence)


  def testNoGrowthOnCorrectlyActiveSegments(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.2,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=3,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.02,
      seed=42)

    previousActiveColumns = [0]
    previousActiveCells = [0,1,2,3]
    activeColumns = [1]
    activeCell = 5

    activeSegment = tm.connections.createSegment(activeCell)
    tm.connections.createSynapse(activeSegment, previousActiveCells[0], .5)
    tm.connections.createSynapse(activeSegment, previousActiveCells[1], .5)
    tm.connections.createSynapse(activeSegment, previousActiveCells[2], .5)

    tm.compute(previousActiveColumns, True)
    tm.compute(activeColumns, True)

    self.assertEqual(3, len(tm.connections.synapsesForSegment(activeSegment)))


  def testReinforceSelectedMatchingSegmentInBurstingColumn(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=3,
      permanenceIncrement=.10,
      permanenceDecrement=.08,
      predictedSegmentDecrement=0.0,
      seed=42)

    previousActiveColumns = [0]
    previousActiveCells = [0,1,2,3]
    activeColumns = [1]
    burstingCells = [4,5,6,7]

    selectedMatchingSegment = tm.connections.createSegment(burstingCells[0])
    as1 = tm.connections.createSynapse(selectedMatchingSegment,
                                       previousActiveCells[0], .3)
    as2 = tm.connections.createSynapse(selectedMatchingSegment,
                                       previousActiveCells[1], .3)
    as3 = tm.connections.createSynapse(selectedMatchingSegment,
                                       previousActiveCells[2], .3)
    is1 = tm.connections.createSynapse(selectedMatchingSegment, 81, .3)

    otherMatchingSegment = tm.connections.createSegment(burstingCells[1])
    tm.connections.createSynapse(otherMatchingSegment,
                                 previousActiveCells[0], .3)
    tm.connections.createSynapse(otherMatchingSegment,
                                 previousActiveCells[1], .3)
    tm.connections.createSynapse(otherMatchingSegment, 81, .3)

    tm.compute(previousActiveColumns, True)
    tm.compute(activeColumns, True)

    self.assertAlmostEqual(.4, tm.connections.dataForSynapse(as1).permanence)
    self.assertAlmostEqual(.4, tm.connections.dataForSynapse(as2).permanence)
    self.assertAlmostEqual(.4, tm.connections.dataForSynapse(as3).permanence)
    self.assertAlmostEqual(.22, tm.connections.dataForSynapse(is1).permanence)


  def testNoChangeToNonselectedMatchingSegmentsInBurstingColumn(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=3,
      permanenceIncrement=.10,
      permanenceDecrement=.08,
      predictedSegmentDecrement=0.0,
      seed=42)

    previousActiveColumns = [0]
    previousActiveCells = [0,1,2,3]
    activeColumns = [1]
    burstingCells = [4,5,6,7]

    selectedMatchingSegment = tm.connections.createSegment(burstingCells[0])
    tm.connections.createSynapse(selectedMatchingSegment,
                                 previousActiveCells[0], .3)
    tm.connections.createSynapse(selectedMatchingSegment,
                                 previousActiveCells[1], .3)
    tm.connections.createSynapse(selectedMatchingSegment,
                                 previousActiveCells[2], .3)
    tm.connections.createSynapse(selectedMatchingSegment, 81, .3)

    otherMatchingSegment = tm.connections.createSegment(burstingCells[1])
    as1 = tm.connections.createSynapse(otherMatchingSegment,
                                       previousActiveCells[0], .3)
    as2 = tm.connections.createSynapse(otherMatchingSegment,
                                       previousActiveCells[1], .3)
    is1 = tm.connections.createSynapse(otherMatchingSegment, 81, .3)

    tm.compute(previousActiveColumns, True)
    tm.compute(activeColumns, True)

    self.assertAlmostEqual(.3, tm.connections.dataForSynapse(as1).permanence)
    self.assertAlmostEqual(.3, tm.connections.dataForSynapse(as2).permanence)
    self.assertAlmostEqual(.3, tm.connections.dataForSynapse(is1).permanence)


  def testNoChangeToMatchingSegmentsInPredictedActiveColumn(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=3,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.0,
      seed=42)

    previousActiveColumns = [0]
    activeColumns = [1]
    previousActiveCells = [0,1,2,3]
    expectedActiveCells = [4]
    otherburstingCells = [5,6,7]

    activeSegment = tm.connections.createSegment(expectedActiveCells[0])
    tm.connections.createSynapse(activeSegment, previousActiveCells[0], .5)
    tm.connections.createSynapse(activeSegment, previousActiveCells[1], .5)
    tm.connections.createSynapse(activeSegment, previousActiveCells[2], .5)
    tm.connections.createSynapse(activeSegment, previousActiveCells[3], .5)

    matchingSegmentOnSameCell = tm.connections.createSegment(
      expectedActiveCells[0])
    s1 = tm.connections.createSynapse(matchingSegmentOnSameCell,
                                      previousActiveCells[0], .3)
    s2 = tm.connections.createSynapse(matchingSegmentOnSameCell,
                                      previousActiveCells[1], .3)

    matchingSegmentOnOtherCell = tm.connections.createSegment(
      otherburstingCells[0])
    s3 = tm.connections.createSynapse(matchingSegmentOnOtherCell,
                                      previousActiveCells[0], .3)
    s4 = tm.connections.createSynapse(matchingSegmentOnOtherCell,
                                      previousActiveCells[1], .3)


    tm.compute(previousActiveColumns, True)
    self.assertEqual(expectedActiveCells, tm.getPredictiveCells())
    tm.compute(activeColumns, True)

    self.assertAlmostEqual(.3, tm.connections.dataForSynapse(s1).permanence)
    self.assertAlmostEqual(.3, tm.connections.dataForSynapse(s2).permanence)
    self.assertAlmostEqual(.3, tm.connections.dataForSynapse(s3).permanence)
    self.assertAlmostEqual(.3, tm.connections.dataForSynapse(s4).permanence)


  def testNoNewSegmentIfNotEnoughWinnerCells(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=3,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.0,
      seed=42)

    zeroColumns = []
    activeColumns = [0]

    tm.compute(zeroColumns, True)
    tm.compute(activeColumns, True)

    self.assertEqual(0, tm.connections.numSegments())


  def testNewSegmentAddSynapsesToSubsetOfWinnerCells(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=2,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.0,
      seed=42)

    previousActiveColumns = [0, 1, 2]
    activeColumns = [4]

    tm.compute(previousActiveColumns, True)

    prevWinnerCells = tm.getWinnerCells() #[0, 8, 7]
    self.assertEqual(3, len(prevWinnerCells))

    tm.compute(activeColumns, True)

    winnerCells = tm.getWinnerCells() #[18]
    self.assertEqual(1, len(winnerCells))
    segments = tm.connections.segmentsForCell(winnerCells[0])
    self.assertEqual(1, len(segments))
    synapses = tm.connections.synapsesForSegment(segments[0])
    self.assertEqual(2, len(synapses))

    for synapse in synapses:
      synapseData = tm.connections.dataForSynapse(synapse)
      self.assertAlmostEqual(.21, synapseData.permanence)
      self.assertTrue(synapseData.presynapticCell in prevWinnerCells)


  def testNewSegmentAddSynapsesToAllWinnerCells(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=4,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.0,
      seed=42)

    previousActiveColumns = [0, 1, 2]
    activeColumns = [4]

    tm.compute(previousActiveColumns)
    prevWinnerCells = sorted(tm.getWinnerCells())
    self.assertEqual(3, len(prevWinnerCells))

    tm.compute(activeColumns)

    winnerCells = tm.getWinnerCells()
    self.assertEqual(1, len(winnerCells))
    segments = list(tm.connections.segmentsForCell(winnerCells[0]))
    self.assertEqual(1, len(segments))
    synapses = tm.connections.synapsesForSegment(segments[0])
    self.assertEqual(3, len(synapses))

    presynapticCells = []
    for synapse in synapses:
      synapseData = tm.connections.dataForSynapse(synapse)
      self.assertAlmostEqual(.21, synapseData.permanence)
      presynapticCells.append(synapseData.presynapticCell)

    presynapticCells = sorted(presynapticCells)
    self.assertEqual(prevWinnerCells, presynapticCells)


  def testMatchingSegmentAddSynapsesToSubsetOfWinnerCells(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=1,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.50,
      minThreshold=1,
      maxNewSynapseCount=3,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.0,
      seed=42)

    previousActiveColumns = [0, 1, 2, 3]
    prevWinnerCells = [0, 1, 2, 3]
    activeColumns = [4]

    matchingSegment = tm.connections.createSegment(4)
    tm.connections.createSynapse(matchingSegment, 0, .5)

    tm.compute(previousActiveColumns, True)
    self.assertEqual(prevWinnerCells, tm.getWinnerCells())
    tm.compute(activeColumns, True)

    synapses = tm.connections.synapsesForSegment(matchingSegment)
    self.assertEqual(3, len(synapses))

    synapses = synapses[1:] # only test the synapses added by compute
    for synapse in synapses:
      synapseData = tm.connections.dataForSynapse(synapse)
      self.assertAlmostEqual(.21, synapseData.permanence)
      self.assertTrue(synapseData.presynapticCell == prevWinnerCells[1] or
                      synapseData.presynapticCell == prevWinnerCells[2] or
                      synapseData.presynapticCell == prevWinnerCells[3])


  def testMatchingSegmentAddSynapsesToAllWinnerCells(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=1,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.50,
      minThreshold=1,
      maxNewSynapseCount=3,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.0,
      seed=42)

    previousActiveColumns = [0, 1]
    prevWinnerCells = [0, 1]
    activeColumns = [4]

    matchingSegment = tm.connections.createSegment(4)
    tm.connections.createSynapse(matchingSegment, 0, .5)

    tm.compute(previousActiveColumns, True)
    self.assertEqual(prevWinnerCells, tm.getWinnerCells())

    tm.compute(activeColumns)

    synapses = tm.connections.synapsesForSegment(matchingSegment)
    self.assertEqual(2, len(synapses))

    synapseData = tm.connections.dataForSynapse(synapses[1])
    self.assertAlmostEqual(.21, synapseData.permanence)
    self.assertEqual(prevWinnerCells[1], synapseData.presynapticCell)


  def testActiveSegmentGrowSynapsesAccordingToPotentialOverlap(self):
    """
    When a segment becomes active, grow synapses to previous winner cells.

    The number of grown synapses is calculated from the "matching segment"
    overlap, not the "active segment" overlap.
    """
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=1,
      activationThreshold=2,
      initialPermanence=.21,
      connectedPermanence=.50,
      minThreshold=1,
      maxNewSynapseCount=4,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.0,
      seed=42)

    # Use 1 cell per column so that we have easy control over the winner cells.
    previousActiveColumns = [0, 1, 2, 3, 4]
    prevWinnerCells = [0, 1, 2, 3, 4]
    activeColumns = [5]

    activeSegment = tm.connections.createSegment(5)
    tm.connections.createSynapse(activeSegment, 0, .5)
    tm.connections.createSynapse(activeSegment, 1, .5)
    tm.connections.createSynapse(activeSegment, 2, .2)

    tm.compute(previousActiveColumns, True)
    self.assertEqual(prevWinnerCells, tm.getWinnerCells())
    tm.compute(activeColumns, True)

    synapses = tm.connections.synapsesForSegment(activeSegment)
    self.assertEqual(4, len(synapses))

    synapse = synapses[3];
    synapseData = tm.connections.dataForSynapse(synapse)
    self.assertAlmostEqual(.21, synapseData.permanence)
    self.assertTrue(synapseData.presynapticCell == prevWinnerCells[3] or
                    synapseData.presynapticCell == prevWinnerCells[4])


  def testDestroyWeakSynapseOnWrongPrediction(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.2,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=4,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.02,
      seed=42)

    previousActiveColumns = [0]
    previousActiveCells = [0, 1, 2, 3]
    activeColumns = [2]
    expectedActiveCells = [5]

    activeSegment = tm.connections.createSegment(expectedActiveCells[0])
    tm.connections.createSynapse(activeSegment, previousActiveCells[0], .5)
    tm.connections.createSynapse(activeSegment, previousActiveCells[1], .5)
    tm.connections.createSynapse(activeSegment, previousActiveCells[2], .5)
    weakActiveSynapse = tm.connections.createSynapse(activeSegment,
                                                     previousActiveCells[3],
                                                     .015)

    tm.compute(previousActiveColumns, True)
    tm.compute(activeColumns, True)

    self.assertTrue(tm.connections.dataForSynapse(weakActiveSynapse).destroyed)


  def testDestroyWeakSynapseOnActiveReinforce(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.2,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=4,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.02,
      seed=42)

    previousActiveColumns = [0]
    previousActiveCells = [0, 1, 2, 3]
    activeColumns = [2]
    activeCell = 5

    activeSegment = tm.connections.createSegment(activeCell)
    tm.connections.createSynapse(activeSegment, previousActiveCells[0], .5)
    tm.connections.createSynapse(activeSegment, previousActiveCells[1], .5)
    tm.connections.createSynapse(activeSegment, previousActiveCells[2], .5)
    weakInactSynapse = tm.connections.createSynapse(activeSegment,
                                                    previousActiveCells[3],
                                                    .009)

    tm.compute(previousActiveColumns, True)
    tm.compute(activeColumns, True)

    self.assertTrue(tm.connections.dataForSynapse(weakInactSynapse).destroyed)


  def testRecycleWeakestSynapseToMakeRoomForNewSynapse(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=1,
      activationThreshold=3,
      initialPermanence=.21,
      connectedPermanence=.50,
      minThreshold=1,
      maxNewSynapseCount=3,
      permanenceIncrement=.02,
      permanenceDecrement=.02,
      predictedSegmentDecrement=0.0,
      seed=42,
      maxSynapsesPerSegment=3)

    prevActiveColumns = [0, 1, 2]
    prevWinnerCells = [0, 1, 2]
    activeColumns = [4]

    matchingSegment = tm.connections.createSegment(4)
    tm.connections.createSynapse(matchingSegment, 81, .6)

    weakestSynapse = tm.connections.createSynapse(matchingSegment, 0, .11)

    tm.compute(prevActiveColumns)
    self.assertEqual(prevWinnerCells, tm.getWinnerCells())
    tm.compute(activeColumns)

    synapseData = tm.connections.dataForSynapse(weakestSynapse)
    self.assertNotEqual(0, synapseData.presynapticCell)

    self.assertFalse(synapseData.destroyed)

    self.assertAlmostEqual(.21, synapseData.permanence)


  def testRecycleLeastRecentlyActiveSegmentToMakeRoomForNewSegment(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=1,
      activationThreshold=3,
      initialPermanence=.50,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=3,
      permanenceIncrement=.02,
      permanenceDecrement=.02,
      predictedSegmentDecrement=0.0,
      seed=42,
      maxSegmentsPerCell=2)

    prevActiveColumns1 = [0, 1, 2]
    prevActiveColumns2 = [3, 4, 5]
    prevActiveColumns3 = [6, 7, 8]
    activeColumns = [9]

    tm.compute(prevActiveColumns1)
    tm.compute(activeColumns)

    self.assertEqual(1, len(tm.connections.segmentsForCell(9)))
    oldestSegment = tm.connections.segmentsForCell(9)[0]
    tm.reset()
    tm.compute(prevActiveColumns2)
    tm.compute(activeColumns)

    self.assertEqual(2, len(tm.connections.segmentsForCell(9)))

    tm.reset()
    tm.compute(prevActiveColumns3)
    tm.compute(activeColumns)
    self.assertEqual(2, len(tm.connections.segmentsForCell(9)))


    synapses = tm.connections.synapsesForSegment(oldestSegment)
    self.assertEqual(3, len(synapses))
    presynapticCells = set()

    for synapseData in tm.connections.dataForSegment(oldestSegment).synapses:
      presynapticCells.add(synapseData.presynapticCell)

    expected = set([6,7,8])
    self.assertEqual(expected, presynapticCells)


  def testDestroySegmentsWithTooFewSynapsesToBeMatching(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.2,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=4,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.02,
      seed=42)

    prevActiveColumns = [0]
    prevActiveCells = [0, 1, 2, 3]
    activeColumns = [2]
    expectedActiveCell = 5

    matchingSegment = tm.connections.createSegment(expectedActiveCell)
    tm.connections.createSynapse(matchingSegment, prevActiveCells[0], .015)
    tm.connections.createSynapse(matchingSegment, prevActiveCells[1], .015)
    tm.connections.createSynapse(matchingSegment, prevActiveCells[2], .015)
    tm.connections.createSynapse(matchingSegment, prevActiveCells[3], .015)

    tm.compute(prevActiveColumns, True)
    tm.compute(activeColumns, True)


    self.assertTrue(tm.connections.dataForSegment(matchingSegment))
    self.assertEqual(0, len(tm.connections.segmentsForCell(expectedActiveCell)))


  def testPunishMatchingSegmentsInInactiveColumns(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.2,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=4,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.02,
      seed=42)

    previousActiveColumns = [0]
    previousActiveCells = [0, 1, 2, 3]
    activeColumns = [1]
    previousInactiveCell = 81

    activeSegment = tm.connections.createSegment(42)
    as1 = tm.connections.createSynapse(activeSegment,
                                       previousActiveCells[0], .5)
    as2 = tm.connections.createSynapse(activeSegment,
                                       previousActiveCells[1], .5)
    as3 = tm.connections.createSynapse(activeSegment,
                                       previousActiveCells[2], .5)
    is1 = tm.connections.createSynapse(activeSegment,
                                       previousInactiveCell, .5)

    matchingSegment = tm.connections.createSegment(43)
    as4 = tm.connections.createSynapse(matchingSegment,
                                       previousActiveCells[0], .5)
    as5 = tm.connections.createSynapse(matchingSegment,
                                       previousActiveCells[1], .5)
    is2 = tm.connections.createSynapse(matchingSegment,
                                       previousInactiveCell, .5)

    tm.compute(previousActiveColumns, True)
    tm.compute(activeColumns, True)

    self.assertAlmostEqual(.48, tm.connections.dataForSynapse(as1).permanence)
    self.assertAlmostEqual(.48, tm.connections.dataForSynapse(as2).permanence)
    self.assertAlmostEqual(.48, tm.connections.dataForSynapse(as3).permanence)
    self.assertAlmostEqual(.48, tm.connections.dataForSynapse(as4).permanence)
    self.assertAlmostEqual(.48, tm.connections.dataForSynapse(as5).permanence)
    self.assertAlmostEqual(.50, tm.connections.dataForSynapse(is1).permanence)
    self.assertAlmostEqual(.50, tm.connections.dataForSynapse(is2).permanence)


  def testAddSegmentToCellWithFewestSegments(self):
    grewOnCell1 = False
    grewOnCell2 = False
    for seed in xrange(100):
      tm = TemporalMemory(
        columnDimensions=[32],
        cellsPerColumn=4,
        activationThreshold=3,
        initialPermanence=.2,
        connectedPermanence=.50,
        minThreshold=2,
        maxNewSynapseCount=4,
        permanenceIncrement=.10,
        permanenceDecrement=.10,
        predictedSegmentDecrement=0.02,
        seed=seed)

      prevActiveColumns = [1, 2, 3, 4]
      activeColumns = [0]
      prevActiveCells = [4, 5, 6, 7]
      nonMatchingCells = [0, 3]
      activeCells = [0, 1, 2, 3]

      segment1 = tm.connections.createSegment(nonMatchingCells[0])
      tm.connections.createSynapse(segment1, prevActiveCells[0], .5)
      segment2 = tm.connections.createSegment(nonMatchingCells[1])
      tm.connections.createSynapse(segment2, prevActiveCells[1], .5)

      tm.compute(prevActiveColumns, True)
      tm.compute(activeColumns, True)

      self.assertEqual(activeCells, tm.getActiveCells())

      self.assertEqual(3, tm.connections.numSegments())
      self.assertEqual(1, len(tm.connections.segmentsForCell(0)))
      self.assertEqual(1, len(tm.connections.segmentsForCell(3)))
      self.assertEqual(1, len(tm.connections.synapsesForSegment(segment1)))
      self.assertEqual(1, len(tm.connections.synapsesForSegment(segment2)))

      segments = tm.connections.segmentsForCell(1)
      if len(segments) == 0:
        segments2 = tm.connections.segmentsForCell(2)
        self.assertFalse(len(segments2) == 0)
        grewOnCell2 = True
        segments.append(segments2[0])
      else:
        grewOnCell1 = True

      self.assertEqual(1, len(segments))
      synapses = tm.connections.synapsesForSegment(segments[0])
      self.assertEqual(4, len(synapses))

      columnChecklist = set(prevActiveColumns)

      for synapse in synapses:
        synapseData = tm.connections.dataForSynapse(synapse)
        self.assertAlmostEqual(.2, synapseData.permanence)

        column = tm.columnForCell(synapseData.presynapticCell)
        self.assertTrue(column in columnChecklist)
        columnChecklist.remove(column)
      self.assertTrue(len(columnChecklist) == 0)

    self.assertTrue(grewOnCell1)
    self.assertTrue(grewOnCell2)


  def testConnectionsNeverChangeWhenLearningDisabled(self):
    tm = TemporalMemory(
      columnDimensions=[32],
      cellsPerColumn=4,
      activationThreshold=3,
      initialPermanence=.2,
      connectedPermanence=.50,
      minThreshold=2,
      maxNewSynapseCount=4,
      permanenceIncrement=.10,
      permanenceDecrement=.10,
      predictedSegmentDecrement=0.02,
      seed=42)

    prevActiveColumns = [0]
    prevActiveCells = [0, 1, 2, 3]
    activeColumns = [1, 2] #1 is predicted, 2 is bursting
    prevInactiveCell = 81
    expectedActiveCells = [4]

    correctActiveSegment = tm.connections.createSegment(expectedActiveCells[0])
    tm.connections.createSynapse(correctActiveSegment, prevActiveCells[0], .5)
    tm.connections.createSynapse(correctActiveSegment, prevActiveCells[1], .5)
    tm.connections.createSynapse(correctActiveSegment, prevActiveCells[2], .5)

    wrongMatchingSegment = tm.connections.createSegment(43)
    tm.connections.createSynapse(wrongMatchingSegment, prevActiveCells[0], .5)
    tm.connections.createSynapse(wrongMatchingSegment, prevActiveCells[1], .5)
    tm.connections.createSynapse(wrongMatchingSegment, prevInactiveCell, .5)

    before = copy.deepcopy(tm.connections)

    tm.compute(prevActiveColumns, False)
    tm.compute(activeColumns, False)

    self.assertEqual(before, tm.connections)


  def testColumnForCell1D(self):
    tm = TemporalMemory(
      columnDimensions=[2048],
      cellsPerColumn=5
    )
    self.assertEqual(tm.columnForCell(0), 0)
    self.assertEqual(tm.columnForCell(4), 0)
    self.assertEqual(tm.columnForCell(5), 1)
    self.assertEqual(tm.columnForCell(10239), 2047)


  def testColumnForCell2D(self):
    tm = TemporalMemory(
      columnDimensions=[64, 64],
      cellsPerColumn=4
    )
    self.assertEqual(tm.columnForCell(0), 0)
    self.assertEqual(tm.columnForCell(3), 0)
    self.assertEqual(tm.columnForCell(4), 1)
    self.assertEqual(tm.columnForCell(16383), 4095)


  def testColumnForCellInvalidCell(self):
    tm = TemporalMemory(
      columnDimensions=[64, 64],
      cellsPerColumn=4
    )

    try:
      tm.columnForCell(16383)
    except IndexError:
      self.fail("IndexError raised unexpectedly")

    args = [16384]
    self.assertRaises(IndexError, tm.columnForCell, *args)

    args = [-1]
    self.assertRaises(IndexError, tm.columnForCell, *args)


  def testCellsForColumn1D(self):
    tm = TemporalMemory(
      columnDimensions=[2048],
      cellsPerColumn=5
    )
    expectedCells = [5, 6, 7, 8, 9]
    self.assertEqual(tm.cellsForColumn(1), expectedCells)


  def testCellsForColumn2D(self):
    tm = TemporalMemory(
      columnDimensions=[64, 64],
      cellsPerColumn=4
    )
    expectedCells = [256, 257, 258, 259]
    self.assertEqual(tm.cellsForColumn(64), expectedCells)


  def testCellsForColumnInvalidColumn(self):
    tm = TemporalMemory(
      columnDimensions=[64, 64],
      cellsPerColumn=4
    )

    try:
      tm.cellsForColumn(4095)
    except IndexError:
      self.fail("IndexError raised unexpectedly")

    args = [4096]
    self.assertRaises(IndexError, tm.cellsForColumn, *args)

    args = [-1]
    self.assertRaises(IndexError, tm.cellsForColumn, *args)


  def testNumberOfColumns(self):
    tm = TemporalMemory(
      columnDimensions=[64, 64],
      cellsPerColumn=32
    )
    self.assertEqual(tm.numberOfColumns(), 64 * 64)


  def testNumberOfCells(self):
    tm = TemporalMemory(
      columnDimensions=[64, 64],
      cellsPerColumn=32
    )
    self.assertEqual(tm.numberOfCells(), 64 * 64 * 32)


  def testMapCellsToColumns(self):
    tm = TemporalMemory(
      columnDimensions=[100],
      cellsPerColumn=4
    )
    columnsForCells = tm.mapCellsToColumns(set([0, 1, 2, 5, 399]))
    self.assertEqual(columnsForCells[0], set([0, 1, 2]))
    self.assertEqual(columnsForCells[1], set([5]))
    self.assertEqual(columnsForCells[99], set([399]))


  @unittest.skipUnless(
    capnp, "pycapnp is not installed, skipping serialization test.")
  def testWriteRead(self):
    tm1 = TemporalMemory(
      columnDimensions=[100],
      cellsPerColumn=4,
      activationThreshold=7,
      initialPermanence=0.37,
      connectedPermanence=0.58,
      minThreshold=4,
      maxNewSynapseCount=18,
      permanenceIncrement=0.23,
      permanenceDecrement=0.08,
      seed=91
    )

    # Run some data through before serializing
    patternMachine = PatternMachine(100, 4)
    sequenceMachine = SequenceMachine(patternMachine)
    sequence = sequenceMachine.generateFromNumbers(range(5))
    for _ in range(3):
      for pattern in sequence:
        tm1.compute(pattern)

    proto1 = TemporalMemoryProto_capnp.TemporalMemoryProto.new_message()
    tm1.write(proto1)

    # Write the proto to a temp file and read it back into a new proto
    with tempfile.TemporaryFile() as f:
      proto1.write(f)
      f.seek(0)
      proto2 = TemporalMemoryProto_capnp.TemporalMemoryProto.read(f)

    # Load the deserialized proto
    tm2 = TemporalMemory.read(proto2)

    # Check that the two temporal memory objects have the same attributes
    self.assertEqual(tm1, tm2)
    # Run a couple records through after deserializing and check results match
    tm1.compute(patternMachine.get(0))
    tm2.compute(patternMachine.get(0))
    self.assertEqual(set(tm1.getActiveCells()), set(tm2.getActiveCells()))
    self.assertEqual(set(tm1.getPredictiveCells()),
                     set(tm2.getPredictiveCells()))
    self.assertEqual(set(tm1.getWinnerCells()), set(tm2.getWinnerCells()))
    self.assertEqual(tm1.connections, tm2.connections)

    tm1.compute(patternMachine.get(3))
    tm2.compute(patternMachine.get(3))
    self.assertEqual(set(tm1.getActiveCells()), set(tm2.getActiveCells()))
    self.assertEqual(set(tm1.getPredictiveCells()),
                     set(tm2.getPredictiveCells()))
    self.assertEqual(set(tm1.getWinnerCells()), set(tm2.getWinnerCells()))
    self.assertEqual(tm1.connections, tm2.connections)


if __name__ == '__main__':
  unittest.main()
