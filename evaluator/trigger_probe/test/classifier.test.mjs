import test from 'node:test'
import assert from 'node:assert/strict'
import { classifyReasoning } from '../src/classifier.mjs'

test('classifies the strong minimal-like opening', () => {
  assert.equal(classifyReasoning('We need inspect the repository.').label, 'minimal-like')
})

test('classifies the strong standard-like opening', () => {
  assert.equal(classifyReasoning('Let me inspect the repository.').label, 'standard-like')
})

test('keeps Need-only continuation ambiguous', () => {
  assert.equal(classifyReasoning('Need inspect the next file.').label, 'ambiguous')
})
