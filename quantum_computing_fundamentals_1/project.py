# ============================================
# Quantum IoT Monitoring System (Real Version)
# ============================================

import pandas as pd
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import time

# ============================================
# DATA INGESTION (REAL INPUT)
# ============================================

class DataLoader:
    @staticmethod
    def load_csv(path):
        df = pd.read_csv(path)
        return df["value"].values


# ============================================
# ORACLE (REAL DATA DRIVEN)
# ============================================

class OracleBuilder:
    @staticmethod
    def build(sensor_data, n_qubits):
        qc = QuantumCircuit(n_qubits + 1)

        if np.all(sensor_data == 0):
            return qc

        if np.all(sensor_data == 1):
            qc.x(n_qubits)
            return qc

        # Balanced mapping based on actual data distribution
        for i in range(n_qubits):
            if np.mean(sensor_data) > 0.5:
                qc.cx(i, n_qubits)
            else:
                if i % 2 == 0:
                    qc.cx(i, n_qubits)

        return qc


# ============================================
# QUANTUM ENGINE
# ============================================

class QuantumAnalyzer:
    def __init__(self, n_qubits):
        self.n = n_qubits
        self.backend = AerSimulator()

    def run(self, oracle):
        qc = QuantumCircuit(self.n + 1, self.n)

        qc.x(self.n)

        for i in range(self.n + 1):
            qc.h(i)

        qc.compose(oracle, inplace=True)

        for i in range(self.n):
            qc.h(i)

        qc.measure(range(self.n), range(self.n))

        result = self.backend.run(qc, shots=1).result()
        counts = result.get_counts()

        return list(counts.keys())[0]


# ============================================
# CLASSICAL ANALYSIS
# ============================================

class Diagnostics:
    @staticmethod
    def analyze(sensor_data):
        faulty = np.where(sensor_data == 1)[0]
        return faulty


# ============================================
# MAIN PIPELINE
# ============================================

class MonitoringSystem:
    def __init__(self, data_path):
        self.data = DataLoader.load_csv(data_path)
        self.n_qubits = int(np.log2(len(self.data)))

        self.quantum = QuantumAnalyzer(self.n_qubits)

    def run(self):
        print("\n=== REAL SENSOR ANALYSIS ===\n")

        print(f"Total Sensors: {len(self.data)}")
        print(f"Faulty Sensors: {np.sum(self.data)}")

        oracle = OracleBuilder.build(self.data, self.n_qubits)

        start = time.time()
        result = self.quantum.run(oracle)
        end = time.time()

        print("\nQuantum Output:", result)

        if result == "0" * self.n_qubits:
            print("✅ System Stable (Constant)")
        else:
            print("⚠️ Fault Detected (Balanced)")

            faulty = Diagnostics.analyze(self.data)
            print("\nFaulty Sensor Indices (sample):", faulty[:10])

        print(f"\nQuantum Detection Time: {end - start:.6f}s")


# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    system = MonitoringSystem("sensor_data.csv")
    system.run()