import assert from 'node:assert/strict'
import { fatEnergyShare, gradeFood } from '../src/grade.ts'

const g = (kcal: number | null, c?: number | null, p?: number | null, f?: number | null) =>
  gradeFood({ kcal_100g: kcal, carbs_g: c, protein_g: p, fat_g: f })

// base bands
assert.equal(g(149)?.grade, 'green')
assert.equal(g(150)?.grade, 'yellow')
assert.equal(g(399)?.grade, 'yellow')
assert.equal(g(400)?.grade, 'red')
assert.equal(g(null), null)

// fat share formula: 10 g fat, 10 g carbs, 10 g protein -> 90 / 170
assert.ok(Math.abs((fatEnergyShare({ kcal_100g: 170, carbs_g: 10, protein_g: 10, fat_g: 10 }) ?? 0) - 90 / 170) < 1e-9)

// green -> yellow: kcal >= 100 and fat share >= 50%
assert.deepEqual(g(120, 2, 3, 10), { grade: 'yellow', fatShare: 90 / 110, fatUpgraded: true })
// green, high fat but kcal < 100: no upgrade
assert.equal(g(99, 1, 1, 10)?.grade, 'green')
// green, kcal >= 100 but fat share < 50%: no upgrade
assert.equal(g(120, 20, 5, 2)?.fatUpgraded, false)

// yellow -> red: kcal >= 250 and fat share >= 50%
assert.equal(g(300, 5, 10, 25)?.grade, 'red')
assert.equal(g(300, 5, 10, 25)?.fatUpgraded, true)
// yellow, high fat but kcal < 250: stays yellow
assert.equal(g(200, 2, 5, 18)?.grade, 'yellow')

// at most one step: red stays red; green never jumps to red
assert.equal(g(600, 10, 10, 60)?.fatUpgraded, false)
assert.equal(g(140, 0, 0, 15)?.grade, 'yellow')

// missing macros: no upgrade
assert.equal(g(300, null, 10, 25)?.grade, 'yellow')
assert.equal(g(300)?.fatUpgraded, false)

console.log('grade tests passed')
