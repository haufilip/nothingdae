"""
Quantum Network Simulator — BB84 + Teleportation
Requires: pip install qiskit qiskit-aer matplotlib pylatexenc
"""

import random
import math
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram, plot_bloch_multivector
from qiskit.quantum_info import Statevector
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings("ignore")

BACKEND = AerSimulator()

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def run_circuit(qc, shots=1):
    """Run a circuit and return the result counts."""
    qc_m = qc.copy()
    result = BACKEND.run(qc_m, shots=shots).result()
    return result.get_counts()

def encode_qubit(bit: int, basis: str) -> QuantumCircuit:
    """
    Encode a classical bit into a qubit.
      basis '+' (rectilinear): |0> or |1>
      basis 'x' (diagonal):   |+> or |->
    """
    qc = QuantumCircuit(1, name=f"enc({bit},{basis})")
    if bit == 1:
        qc.x(0)          # flip to |1>
    if basis == 'x':
        qc.h(0)          # rotate to diagonal basis
    return qc

def measure_qubit(basis: str) -> QuantumCircuit:
    """
    Measure a qubit in a given basis.
      basis '+': standard Z measurement
      basis 'x': Hadamard then Z measurement
    """
    qc = QuantumCircuit(1, 1, name=f"meas({basis})")
    if basis == 'x':
        qc.h(0)
    qc.measure(0, 0)
    return qc

# ─────────────────────────────────────────────
#  BB84 PROTOCOL
# ─────────────────────────────────────────────

def bb84_protocol(n_bits: int = 20, eve_present: bool = False):
    """
    Simulate the full BB84 quantum key distribution protocol.

    Steps:
      1. Alice prepares n qubits in random bases/bits
      2. (Optional) Eve intercepts each qubit with a random basis
      3. Bob measures each qubit in a random basis
      4. Alice & Bob sift: keep only matching-basis bits
      5. Error check on sample — if error rate > 11%, abort

    Returns a dict with full results.
    """
    print("\n" + "═"*60)
    print("  BB84 Quantum Key Distribution")
    print(f"  n={n_bits} qubits  |  eavesdropper={'YES ⚠' if eve_present else 'no'}")
    print("═"*60)

    alice_bits   = [random.randint(0, 1) for _ in range(n_bits)]
    alice_bases  = [random.choice(['+', 'x']) for _ in range(n_bits)]
    bob_bases    = [random.choice(['+', 'x']) for _ in range(n_bits)]

    eve_bases    = [random.choice(['+', 'x']) for _ in range(n_bits)] if eve_present else None
    eve_bits     = []
    bob_bits     = []
    circuits     = []

    for i in range(n_bits):
        # --- Alice encodes ---
        enc = encode_qubit(alice_bits[i], alice_bases[i])

        if eve_present:
            # Eve intercepts: measure then re-encode
            eve_qc = enc.copy()
            meas_e = measure_qubit(eve_bases[i])
            combined = QuantumCircuit(1, 1)
            combined.compose(enc, inplace=True)
            combined.compose(meas_e, inplace=True)
            counts_e = run_circuit(combined, shots=1)
            e_bit = int(list(counts_e.keys())[0])
            eve_bits.append(e_bit)
            # Eve re-encodes what she measured and sends to Bob
            enc = encode_qubit(e_bit, eve_bases[i])
        else:
            eve_bits.append(None)

        # --- Bob measures ---
        full_qc = QuantumCircuit(1, 1)
        full_qc.compose(enc, inplace=True)
        meas_b = measure_qubit(bob_bases[i])
        full_qc.compose(meas_b, inplace=True)
        counts_b = run_circuit(full_qc, shots=1)
        b_bit = int(list(counts_b.keys())[0])
        bob_bits.append(b_bit)
        circuits.append(full_qc)

    # --- Sifting ---
    sifted_indices = [i for i in range(n_bits) if alice_bases[i] == bob_bases[i]]
    alice_key = [alice_bits[i] for i in sifted_indices]
    bob_key   = [bob_bits[i]   for i in sifted_indices]

    # --- Error estimation (use first half of sifted key) ---
    sample_size = max(1, len(sifted_indices) // 2)
    errors = sum(1 for i in range(sample_size) if alice_key[i] != bob_key[i])
    error_rate = errors / sample_size if sample_size else 0
    threshold = 0.11
    secure = error_rate <= threshold
    final_key = alice_key[sample_size:]  # second half is the actual secret key

    # --- Print table ---
    print(f"\n{'#':>3} │ A-basis │ A-bit │ {'Eve-basis':^9} │ {'Eve-bit':^7} │ B-basis │ B-bit │ match │ keep")
    print("─"*80)
    for i in range(n_bits):
        match = alice_bases[i] == bob_bases[i]
        keep  = match
        eb    = eve_bases[i] if eve_present else "—"
        ebit  = str(eve_bits[i]) if eve_present else "—"
        flag  = "✓" if keep else " "
        err   = " ←ERR" if (keep and alice_bits[i] != bob_bits[i]) else ""
        print(f"{i+1:>3} │  {alice_bases[i]:^7} │   {alice_bits[i]}   │  {eb:^9} │   {ebit:^5} │  {bob_bases[i]:^7} │   {bob_bits[i]}   │   {flag}   │ {'keep' if keep else 'drop'}{err}")

    print("\n" + "─"*60)
    print(f"  Qubits sent        : {n_bits}")
    print(f"  Sifted key length  : {len(sifted_indices)}")
    print(f"  Sample errors      : {errors}/{sample_size}  ({error_rate*100:.1f}%)")
    print(f"  Threshold          : {threshold*100:.0f}%")
    print(f"  Eavesdropper       : {'DETECTED — key discarded ⚠' if not secure else 'not detected'}")
    if secure and final_key:
        print(f"  Secret key         : {''.join(str(b) for b in final_key)}")
    print("─"*60)

    return {
        "n_bits": n_bits, "alice_bits": alice_bits, "alice_bases": alice_bases,
        "bob_bases": bob_bases, "bob_bits": bob_bits, "eve_bases": eve_bases,
        "eve_bits": eve_bits, "sifted_indices": sifted_indices,
        "alice_key": alice_key, "bob_key": bob_key, "error_rate": error_rate,
        "secure": secure, "final_key": final_key, "circuits": circuits,
    }

# ─────────────────────────────────────────────
#  QUANTUM TELEPORTATION
# ─────────────────────────────────────────────

def teleportation_protocol(state: str = "plus"):
    """
    Simulate quantum teleportation of a qubit from Alice to Bob.

    The state to teleport:
      'zero'  → |0⟩
      'one'   → |1⟩
      'plus'  → |+⟩  = (|0⟩+|1⟩)/√2
      'minus' → |−⟩  = (|0⟩−|1⟩)/√2
      'i'     → |i⟩  = (|0⟩+i|1⟩)/√2

    Returns the full circuit and measurement counts.
    """
    print("\n" + "═"*60)
    print("  Quantum Teleportation")
    print(f"  Teleporting state: |{state}⟩")
    print("═"*60)

    # Registers:
    #   q[0] = Alice's message qubit (the state to teleport)
    #   q[1] = Alice's half of the Bell pair
    #   q[2] = Bob's half of the Bell pair
    msg   = QuantumRegister(1, 'msg')
    alice = QuantumRegister(1, 'alice')
    bob   = QuantumRegister(1, 'bob')
    c_alice = ClassicalRegister(2, 'c_alice')  # Alice's 2 classical bits
    c_bob   = ClassicalRegister(1, 'c_bob')    # Bob's final measurement

    qc = QuantumCircuit(msg, alice, bob, c_alice, c_bob)

    # ── Step 1: Prepare message qubit ──────────────────────────
    qc.barrier(label="Prepare |ψ⟩")
    if state == 'one':
        qc.x(msg[0])
    elif state == 'plus':
        qc.h(msg[0])
    elif state == 'minus':
        qc.x(msg[0]); qc.h(msg[0])
    elif state == 'i':
        qc.h(msg[0]); qc.s(msg[0])

    # ── Step 2: Create Bell pair (entanglement) ─────────────────
    qc.barrier(label="Bell pair")
    qc.h(alice[0])
    qc.cx(alice[0], bob[0])

    # ── Step 3: Alice's Bell measurement ───────────────────────
    qc.barrier(label="Alice Bell meas")
    qc.cx(msg[0], alice[0])
    qc.h(msg[0])
    qc.measure(msg[0],   c_alice[1])
    qc.measure(alice[0], c_alice[0])

    # ── Step 4: Bob's correction (classically controlled) ───────
    qc.barrier(label="Bob correction")
    with qc.if_else((c_alice[0], 1)):
        qc.x(bob[0])
    with qc.if_else((c_alice[1], 1)):
        qc.z(bob[0])

    # ── Step 5: Bob measures to verify ──────────────────────────
    qc.barrier(label="Bob measures")
    qc.measure(bob[0], c_bob[0])

    print("\nCircuit:")
    print(qc.draw(output='text', fold=90))

    counts = run_circuit(qc, shots=1024)
    print(f"\nMeasurement counts (1024 shots): {counts}")

    # Interpret: c_bob should mirror the original state
    # For |0⟩ → mostly '0', for |1⟩ → mostly '1', for |+⟩ → ~50/50
    bob_counts = {}
    for key, val in counts.items():
        # key format: "c_alice c_bob" → last char is Bob's bit
        bob_bit = key.split()[-1] if ' ' in key else key[-1]
        bob_counts[bob_bit] = bob_counts.get(bob_bit, 0) + val

    total = sum(bob_counts.values())
    print("\nBob's qubit measurement (verifying teleportation):")
    for k, v in sorted(bob_counts.items()):
        bar = "█" * int(30 * v / total)
        print(f"  |{k}⟩  {bar}  {v/total*100:.1f}%")

    expected = {
        'zero': '|0⟩ 100%', 'one': '|1⟩ 100%',
        'plus': '|0⟩ ~50%, |1⟩ ~50%',
        'minus': '|0⟩ ~50%, |1⟩ ~50%',
        'i': '|0⟩ ~50%, |1⟩ ~50%'
    }
    print(f"\n  Expected distribution: {expected.get(state,'—')}")
    print("  ✓ Quantum state teleported — no quantum info sent classically!")
    print("─"*60)

    return {"circuit": qc, "counts": counts, "bob_counts": bob_counts, "state": state}

# ─────────────────────────────────────────────
#  VISUALISATION
# ─────────────────────────────────────────────

def plot_bb84_results(result: dict):
    """Plot BB84 sifting, error analysis and key bit chart."""
    fig = plt.figure(figsize=(14, 9))
    fig.patch.set_facecolor('#f9f9f7')
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

    n = result['n_bits']
    indices = list(range(n))

    # ── 1. Base match plot ───────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.set_facecolor('#f9f9f7')
    match_colors = []
    for i in indices:
        if result['alice_bases'][i] == result['bob_bases'][i]:
            match_colors.append('#1D9E75' if result['alice_bits'][i] == result['bob_bits'][i] else '#E24B4A')
        else:
            match_colors.append('#D3D1C7')
    bars = ax1.bar(indices, [1]*n, color=match_colors, width=0.8, edgecolor='white', linewidth=0.5)
    ax1.set_yticks([])
    ax1.set_xticks(indices)
    ax1.set_xticklabels([str(i+1) for i in indices], fontsize=8)
    ax1.set_title('Qubit-by-qubit: basis match & errors', fontsize=12, fontweight='bold', pad=8)
    ax1.set_xlabel('Qubit index', fontsize=10)
    ax1.spines[:].set_visible(False)
    legend_patches = [
        mpatches.Patch(color='#1D9E75', label='matched basis, no error'),
        mpatches.Patch(color='#E24B4A', label='matched basis, bit error (Eve!)'),
        mpatches.Patch(color='#D3D1C7', label='basis mismatch (discarded)'),
    ]
    ax1.legend(handles=legend_patches, loc='upper right', fontsize=8, framealpha=0.8)

    # ── 2. Pie: kept vs dropped ──────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.set_facecolor('#f9f9f7')
    kept = len(result['sifted_indices'])
    dropped = n - kept
    wedges, texts, autotexts = ax2.pie(
        [kept, dropped], labels=['kept', 'discarded'],
        colors=['#378ADD', '#D3D1C7'], autopct='%1.0f%%',
        startangle=90, textprops={'fontsize': 10},
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}
    )
    ax2.set_title('Sifting result', fontsize=12, fontweight='bold')

    # ── 3. Alice vs Bob key bits ─────────────────────────────────
    ax3 = fig.add_subplot(gs[1, :2])
    ax3.set_facecolor('#f9f9f7')
    si = result['sifted_indices']
    ak = result['alice_key']
    bk = result['bob_key']
    x = list(range(len(si)))
    ax3.step(x, ak, where='mid', color='#185FA5', linewidth=2, label="Alice's sifted key")
    ax3.step(x, bk, where='mid', color='#E24B4A', linewidth=1.5, linestyle='--', label="Bob's sifted key")
    for xi, (a, b) in enumerate(zip(ak, bk)):
        if a != b:
            ax3.axvspan(xi-0.4, xi+0.4, color='#FCEBEB', alpha=0.7, zorder=0)
    ax3.set_yticks([0, 1]); ax3.set_yticklabels(['0', '1'])
    ax3.set_xlabel('Sifted key index', fontsize=10)
    ax3.set_title('Alice vs Bob sifted key bits', fontsize=12, fontweight='bold', pad=8)
    ax3.legend(fontsize=9)
    ax3.spines['top'].set_visible(False); ax3.spines['right'].set_visible(False)
    ax3.set_facecolor('#f9f9f7')

    # ── 4. Security summary ──────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 2])
    ax4.set_facecolor('#f9f9f7')
    ax4.axis('off')
    er = result['error_rate'] * 100
    secure = result['secure']
    color = '#27500A' if secure else '#791F1F'
    bg    = '#EAF3DE' if secure else '#FCEBEB'
    status = 'SECURE' if secure else 'BREACHED'
    box = FancyBboxPatch((0.05, 0.1), 0.9, 0.8, boxstyle="round,pad=0.05",
                          facecolor=bg, edgecolor=color, linewidth=1.5,
                          transform=ax4.transAxes)
    ax4.add_patch(box)
    ax4.text(0.5, 0.78, status, ha='center', va='center', fontsize=22, fontweight='bold',
             color=color, transform=ax4.transAxes)
    ax4.text(0.5, 0.58, f'error rate: {er:.1f}%', ha='center', va='center',
             fontsize=13, color=color, transform=ax4.transAxes)
    ax4.text(0.5, 0.42, f'threshold: 11%', ha='center', va='center',
             fontsize=11, color='#888780', transform=ax4.transAxes)
    ax4.text(0.5, 0.26, f'key length: {len(result["final_key"])} bits', ha='center',
             va='center', fontsize=11, color=color, transform=ax4.transAxes)
    eve_label = 'eavesdropper: ON' if any(e is not None for e in result['eve_bits']) else 'eavesdropper: off'
    ax4.text(0.5, 0.13, eve_label, ha='center', va='center', fontsize=10,
             color='#E24B4A' if not secure else '#888780', transform=ax4.transAxes)

    fig.suptitle('BB84 Quantum Key Distribution — Simulation Results',
                 fontsize=14, fontweight='bold', y=0.98)
    plt.savefig('/mnt/user-data/outputs/bb84_results.png', dpi=150, bbox_inches='tight',
                facecolor='#f9f9f7')
    print("\n  [saved] bb84_results.png")
    plt.show()


def plot_teleportation_results(result: dict):
    """Plot teleportation circuit and Bob's output histogram."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor('#f9f9f7')

    # ── Circuit diagram ──────────────────────────────────────────
    ax1 = axes[0]
    ax1.set_facecolor('#f9f9f7')
    ax1.axis('off')
    qc = result['circuit']
    circuit_fig = qc.draw(output='mpl', style={'backgroundcolor': '#f9f9f7',
                                                'linecolor': '#2C2C2A',
                                                'textcolor': '#2C2C2A'})
    circuit_fig.savefig('/tmp/tele_circuit.png', dpi=120, bbox_inches='tight',
                        facecolor='#f9f9f7')
    plt.close(circuit_fig)
    img = plt.imread('/tmp/tele_circuit.png')
    ax1.imshow(img)
    ax1.set_title(f'Teleportation circuit  |  state: |{result["state"]}⟩',
                  fontsize=12, fontweight='bold', pad=8)

    # ── Bob's histogram ──────────────────────────────────────────
    ax2 = axes[1]
    ax2.set_facecolor('#f9f9f7')
    bc = result['bob_counts']
    total = sum(bc.values())
    bars = ax2.bar(list(bc.keys()), [v/total*100 for v in bc.values()],
                   color=['#185FA5', '#1D9E75'][:len(bc)],
                   edgecolor='white', linewidth=1.2, width=0.5)
    for bar, (k, v) in zip(bars, bc.items()):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                 f'{v/total*100:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='500')
    ax2.set_ylabel('Probability (%)', fontsize=11)
    ax2.set_xlabel("Bob's measured bit", fontsize=11)
    ax2.set_title("Bob's output distribution (1024 shots)", fontsize=12, fontweight='bold', pad=8)
    ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
    ax2.set_ylim(0, 115)
    ax2.set_facecolor('#f9f9f7')

    note = {
        'zero':  '|0⟩ teleported → Bob should measure |0⟩ always',
        'one':   '|1⟩ teleported → Bob should measure |1⟩ always',
        'plus':  '|+⟩ teleported → Bob measures |0⟩ or |1⟩ with equal 50/50 probability',
        'minus': '|−⟩ teleported → Bob measures |0⟩ or |1⟩ with equal 50/50 probability',
        'i':     '|i⟩ teleported → Bob measures ~50/50 (Y-basis state)',
    }
    fig.text(0.5, 0.01, note.get(result['state'], ''), ha='center', fontsize=10,
             color='#5F5E5A', style='italic')

    fig.suptitle('Quantum Teleportation — Simulation Results',
                 fontsize=14, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/teleportation_results.png', dpi=150,
                bbox_inches='tight', facecolor='#f9f9f7')
    print("  [saved] teleportation_results.png")
    plt.show()


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":

    print("\n╔══════════════════════════════════════════════════╗")
    print("║   Quantum Network Simulator (Qiskit)             ║")
    print("║   BB84 Key Distribution + Quantum Teleportation  ║")
    print("╚══════════════════════════════════════════════════╝")

    # ── Run 1: BB84 without Eve ──────────────────────────────────
    result_no_eve = bb84_protocol(n_bits=20, eve_present=False)
    plot_bb84_results(result_no_eve)

    # ── Run 2: BB84 with Eve ─────────────────────────────────────
    result_eve = bb84_protocol(n_bits=20, eve_present=True)
    plot_bb84_results(result_eve)

    # ── Run 3: Teleportation of |+⟩ ─────────────────────────────
    tele_plus = teleportation_protocol(state='plus')
    plot_teleportation_results(tele_plus)

    # ── Run 4: Teleportation of |1⟩ ─────────────────────────────
    tele_one = teleportation_protocol(state='one')
    plot_teleportation_results(tele_one)

    print("\n✓ All simulations complete.")
    print("  Outputs saved: bb84_results.png, teleportation_results.png")
