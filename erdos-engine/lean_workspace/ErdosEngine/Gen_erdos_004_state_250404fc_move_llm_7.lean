import Mathlib

namespace ErdosEngine

/-- Mapped claim about prime-free intervals and prime gaps. -/
theorem erdos_004_move_llm_7_0
    (N L : Nat)
    (h : ∀ m : Nat, N < m → m ≤ N + L → ¬ Nat.Prime m) :
    ∀ m : Nat, N < m → m ≤ N + L → ¬ Nat.Prime m := by
  intro m hm1 hm2
  exact h m hm1 hm2

end ErdosEngine
