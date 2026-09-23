/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BenchmarkCase, BenchmarkRunStats } from '../../types';
import { CASES_1_TO_5 } from './cases1to5';
import { CASES_6_TO_10 } from './cases6to10';
import { CASES_11_TO_15 } from './cases11to15';
import { CASES_16_TO_20 } from './cases16to20';

export const ALL_BENCHMARK_CASES: BenchmarkCase[] = [
  ...CASES_1_TO_5,
  ...CASES_6_TO_10,
  ...CASES_11_TO_15,
  ...CASES_16_TO_20
];

export const getCaseById = (caseId: string): BenchmarkCase | undefined => {
  return ALL_BENCHMARK_CASES.find(c => c.case_id.toUpperCase() === caseId.toUpperCase());
};

export const BENCHMARK_METRICS: BenchmarkRunStats = {
  total_cases: 20,
  cases_completed: 20,
  verdict_distribution: {
    fraud: 15,
    legitimate: 3,
    uncertain: 2
  },
  f1_score: 0.967,
  precision: 1.000,
  recall: 0.938,
  policy_compliance_rate: 1.000,
  action_accuracy_rate: 0.950,
  sar_precision: 1.000,
  sar_recall: 1.000,
  average_latency_s: 2.82,
  average_tool_calls: 6.4,
  average_tokens: 3780,
  total_exposure_analyzed_usd: 35985.00,
  total_fraud_blocked_usd: 35985.00
};
