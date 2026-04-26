import Mathlib

namespace ErdosEngine

theorem erdos_004_move_fallback_1_0
    (A B C : Nat)
    (hAB : A = B)
    (hC : C = A) :
    C = B := by
  simpa [hAB] using hC

end ErdosEngine
