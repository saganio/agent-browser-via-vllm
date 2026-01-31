import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { apiClient } from '@/api/client';
import { XrayTestSet, XrayTest, ExecuteTestSetResponse } from '@/types';
import { TkButton, TkCard } from '@takeoff-ui/react';
import { format } from 'date-fns';

export function TestSetDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [testSet, setTestSet] = useState<XrayTestSet | null>(null);
  const [tests, setTests] = useState<XrayTest[]>([]);
  const [selectedTests, setSelectedTests] = useState<Set<number>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<ExecuteTestSetResponse | null>(null);
  const [expandedTest, setExpandedTest] = useState<number | null>(null);

  useEffect(() => {
    if (id) {
      loadTestSet();
      loadTests();
    }
  }, [id]);

  const loadTestSet = async () => {
    try {
      const data = await apiClient.getXrayTestSet(Number(id));
      setTestSet(data);
    } catch (error) {
      console.error('Failed to load test set:', error);
    }
  };

  const loadTests = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getXrayTestsInTestSet(Number(id), { page_size: 100 });
      setTests(data.items);
    } catch (error) {
      console.error('Failed to load tests:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleTestSelection = (testId: number) => {
    const newSelected = new Set(selectedTests);
    if (newSelected.has(testId)) {
      newSelected.delete(testId);
    } else {
      newSelected.add(testId);
    }
    setSelectedTests(newSelected);
  };

  const selectAll = () => {
    if (selectedTests.size === tests.length) {
      setSelectedTests(new Set());
    } else {
      setSelectedTests(new Set(tests.map(t => t.id)));
    }
  };

  const handleExecute = async () => {
    if (!testSet) return;
    
    setIsExecuting(true);
    setExecutionResult(null);
    
    try {
      const result = await apiClient.executeXrayTestSet({
        test_set_id: testSet.id,
        test_ids: selectedTests.size > 0 ? Array.from(selectedTests) : undefined,
      });
      setExecutionResult(result);
    } catch (error) {
      console.error('Failed to execute:', error);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleExecuteSingleTest = async (testId: number) => {
    setIsExecuting(true);
    try {
      const result = await apiClient.executeXrayTest({ xray_test_id: testId });
      navigate(`/tests/${result.test_run_id}`);
    } catch (error) {
      console.error('Failed to execute test:', error);
      setIsExecuting(false);
    }
  };

  const getTestTypeBadge = (type: string) => {
    switch (type) {
      case 'gherkin':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'manual':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  if (!testSet && !isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-slate-800 mb-2">Test Set Not Found</h2>
          <Link to="/test-sets">
            <TkButton variant="primary" label="Back to Test Sets" />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/test-sets')}
            className="p-2 text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            {testSet && (
              <>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-mono text-slate-500">{testSet.xray_issue_key}</span>
                </div>
                <h1 className="text-2xl font-bold text-slate-800">{testSet.name}</h1>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <TkButton
            variant="primary"
            label={isExecuting ? 'Executing...' : (selectedTests.size > 0 ? `Execute ${selectedTests.size} Tests` : 'Execute All')}
            disabled={isExecuting || tests.length === 0}
            onClick={handleExecute}
          />
        </div>
      </div>

      {/* Test set info */}
      {testSet && (
        <TkCard>
          <div className="p-6 bg-white border border-slate-200 rounded-lg shadow-sm">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm text-slate-500 mb-1">Description</p>
                <p className="text-slate-800">{testSet.description || 'No description'}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500 mb-1">Tests</p>
                <p className="text-2xl font-bold text-slate-800">{testSet.test_count}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500 mb-1">Last Synced</p>
                <p className="text-slate-800">
                  {testSet.last_synced_at 
                    ? format(new Date(testSet.last_synced_at), 'MMM d, yyyy HH:mm')
                    : 'Never'}
                </p>
              </div>
            </div>
            
            {/* Labels */}
            {(testSet.labels.length > 0 || testSet.components.length > 0) && (
              <div className="mt-4 pt-4 border-t border-slate-200">
                <div className="flex flex-wrap gap-2">
                  {testSet.labels.map((label, i) => (
                    <span key={`label-${i}`} className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded">
                      {label}
                    </span>
                  ))}
                  {testSet.components.map((comp, i) => (
                    <span key={`comp-${i}`} className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
                      {comp}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </TkCard>
      )}

      {/* Execution result */}
      {executionResult && (
        <div className="p-4 bg-green-100 border border-green-200 rounded-lg">
          <h3 className="font-semibold text-green-800 mb-2">{executionResult.message}</h3>
          <div className="space-y-2">
            {executionResult.test_runs.map((tr) => (
              <div key={tr.test_run_id} className="flex items-center justify-between">
                <span className="text-sm text-green-700">
                  {tr.xray_test_key} - {tr.test_name}
                </span>
                <Link
                  to={`/tests/${tr.test_run_id}`}
                  className="text-sm text-green-800 hover:underline"
                >
                  View Run #{tr.test_run_id}
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tests list */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">Tests</h2>
          <button
            onClick={selectAll}
            className="text-sm text-blue-600 hover:text-blue-500"
          >
            {selectedTests.size === tests.length ? 'Deselect All' : 'Select All'}
          </button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : tests.length > 0 ? (
          <div className="space-y-3">
            {tests.map((test) => (
              <TkCard key={test.id}>
                <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
                  <div 
                    className="p-4 flex items-center gap-4 cursor-pointer hover:bg-slate-50"
                    onClick={() => setExpandedTest(expandedTest === test.id ? null : test.id)}
                  >
                    {/* Checkbox */}
                    <input
                      type="checkbox"
                      checked={selectedTests.has(test.id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        toggleTestSelection(test.id);
                      }}
                      className="w-4 h-4 rounded border-slate-300 text-blue-500 focus:ring-blue-500"
                    />
                    
                    {/* Expand icon */}
                    <svg 
                      className={`w-4 h-4 text-slate-400 transition-transform ${expandedTest === test.id ? 'rotate-90' : ''}`}
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    
                    {/* Test info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono text-slate-500">{test.xray_issue_key}</span>
                        <span className={`px-2 py-0.5 text-xs font-medium rounded border ${getTestTypeBadge(test.test_type)}`}>
                          {test.test_type}
                        </span>
                        {test.priority && (
                          <span className="px-2 py-0.5 text-xs bg-slate-100 text-slate-600 rounded">
                            {test.priority}
                          </span>
                        )}
                      </div>
                      <h3 className="text-slate-800 font-medium truncate">{test.name}</h3>
                    </div>
                    
                    {/* Step count */}
                    <div className="text-sm text-slate-500">
                      {test.step_count} step{test.step_count !== 1 ? 's' : ''}
                    </div>
                    
                    {/* Execute button */}
                    <TkButton
                      variant="secondary"
                      label="Run"
                      onClick={(e: React.MouseEvent) => {
                        e.stopPropagation();
                        handleExecuteSingleTest(test.id);
                      }}
                      disabled={isExecuting}
                    />
                  </div>
                  
                  {/* Expanded content */}
                  {expandedTest === test.id && (
                    <div className="px-4 pb-4 pt-2 border-t border-slate-100">
                      {test.description && (
                        <div className="mb-4">
                          <p className="text-sm text-slate-500 mb-1">Description</p>
                          <p className="text-sm text-slate-700">{test.description}</p>
                        </div>
                      )}
                      
                      {test.preconditions && (
                        <div className="mb-4">
                          <p className="text-sm text-slate-500 mb-1">Preconditions</p>
                          <p className="text-sm text-slate-700 whitespace-pre-wrap">{test.preconditions}</p>
                        </div>
                      )}
                      
                      {/* Show steps based on type */}
                      {test.test_type === 'gherkin' && test.gherkin_scenario && (
                        <div>
                          <p className="text-sm text-slate-500 mb-2">Gherkin Scenario</p>
                          <pre className="p-3 bg-slate-100 rounded-lg text-sm text-slate-700 overflow-x-auto whitespace-pre-wrap">
                            {test.gherkin_scenario}
                          </pre>
                        </div>
                      )}
                      
                      {test.test_type === 'manual' && test.manual_steps.length > 0 && (
                        <div>
                          <p className="text-sm text-slate-500 mb-2">Manual Steps</p>
                          <div className="space-y-2">
                            {test.manual_steps.map((step, idx) => (
                              <div key={idx} className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                                <div className="flex items-start gap-3">
                                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-medium">
                                    {step.index + 1}
                                  </span>
                                  <div className="flex-1">
                                    <p className="text-sm text-slate-700">{step.action}</p>
                                    {step.data && (
                                      <p className="text-xs text-slate-500 mt-1">
                                        <span className="font-medium">Data:</span> {step.data}
                                      </p>
                                    )}
                                    {step.expected && (
                                      <p className="text-xs text-green-600 mt-1">
                                        <span className="font-medium">Expected:</span> {step.expected}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </TkCard>
            ))}
          </div>
        ) : (
          <TkCard>
            <div className="p-8 text-center bg-white border border-slate-200 rounded-lg">
              <p className="text-slate-500">No tests in this test set</p>
            </div>
          </TkCard>
        )}
      </div>
    </div>
  );
}
