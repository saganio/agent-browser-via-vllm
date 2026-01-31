import { useState, useEffect, useRef } from 'react';
import { apiClient } from '@/api/client';
import { Project, TestRun, WSMessage } from '@/types';
import { TkButton, TkTextarea, TkCard } from '@takeoff-ui/react';

export function TestRunner() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  const [command, setCommand] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [messages, setMessages] = useState<WSMessage[]>([]);
  const [currentTestRun, setCurrentTestRun] = useState<TestRun | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadProjects();
    return () => {
      wsRef.current?.close();
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadProjects = async () => {
    try {
      const data = await apiClient.getProjects({ page_size: 100 }) as { items: Project[] };
      setProjects(data.items);
      if (data.items.length > 0 && !selectedProject) {
        setSelectedProject(data.items[0].id);
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
  };

  const executeTest = async () => {
    if (!selectedProject || !command.trim()) return;

    setIsExecuting(true);
    setMessages([]);

    try {
      // Create test run
      const testRun = await apiClient.executeTest(selectedProject, command) as TestRun;
      setCurrentTestRun(testRun);

      // Connect to WebSocket for real-time updates
      const token = apiClient.getAccessToken();
      const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/tests/${testRun.id}/execute?token=${token}`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const message: WSMessage = JSON.parse(event.data);
        
        if (message.type === 'ping') return;
        
        setMessages(prev => [...prev, message]);

        if (message.type === 'complete' || message.type === 'error' || message.type === 'cancelled') {
          setIsExecuting(false);
        }
      };

      ws.onerror = () => {
        setIsExecuting(false);
        setMessages(prev => [...prev, {
          type: 'error',
          test_run_id: testRun.id,
          data: { error: 'WebSocket connection error' }
        }]);
      };

      ws.onclose = () => {
        setIsExecuting(false);
      };

    } catch (error) {
      setIsExecuting(false);
      setMessages([{
        type: 'error',
        test_run_id: 0,
        data: { error: error instanceof Error ? error.message : 'Failed to start test' }
      }]);
    }
  };

  const cancelTest = () => {
    if (currentTestRun) {
      wsRef.current?.send(JSON.stringify({ action: 'cancel' }));
    }
  };

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'status':
        return (
          <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
            <svg className="w-3 h-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
      case 'tool_call':
        return (
          <div className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center">
            <svg className="w-3 h-3 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            </svg>
          </div>
        );
      case 'tool_result':
        return (
          <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center">
            <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        );
      case 'llm_response':
        return (
          <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
            <svg className="w-3 h-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
        );
      case 'complete':
        return (
          <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center">
            <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
      case 'error':
        return (
          <div className="w-6 h-6 bg-red-100 rounded-full flex items-center justify-center">
            <svg className="w-3 h-3 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
      default:
        return null;
    }
  };

  const renderMessageContent = (msg: WSMessage) => {
    const data = msg.data;
    
    switch (msg.type) {
      case 'status':
        return <p className="text-slate-600">{data.message as string}</p>;
      
      case 'tool_call':
        return (
          <div>
            <p className="text-purple-600 font-medium">{data.tool_name as string}</p>
            <pre className="mt-2 p-2 bg-slate-100 rounded text-xs text-slate-600 overflow-x-auto">
              {JSON.stringify(data.arguments, null, 2)}
            </pre>
          </div>
        );
      
      case 'tool_result':
        const result = data.result as { success: boolean; data?: unknown; error?: string };
        const resultDataStr = result.data !== undefined 
          ? (typeof result.data === 'string' ? result.data : JSON.stringify(result.data, null, 2))
          : null;
        return (
          <div>
            <p className={`font-medium ${result.success ? 'text-green-600' : 'text-red-600'}`}>
              {data.tool_name as string}: {result.success ? 'Success' : 'Failed'}
            </p>
            {resultDataStr && (
              <pre className="mt-2 p-2 bg-slate-100 rounded text-xs text-slate-600 overflow-x-auto max-h-40">
                {resultDataStr}
              </pre>
            )}
            {result.error && (
              <p className="mt-2 text-sm text-red-600">{result.error}</p>
            )}
          </div>
        );
      
      case 'llm_response':
        return <p className="text-slate-600 whitespace-pre-wrap">{data.content as string}</p>;
      
      case 'complete':
        return <p className="text-green-600 font-medium">{data.message as string}</p>;
      
      case 'error':
        return <p className="text-red-600">{data.error as string}</p>;
      
      default:
        return <pre className="text-xs text-slate-500">{JSON.stringify(data, null, 2)}</pre>;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Test Runner</h1>
        <p className="text-slate-500 mt-1">Execute browser tests using natural language commands</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input panel */}
        <TkCard>
          <div className="p-6 space-y-4 bg-white rounded-lg border border-slate-200">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Project</label>
              <select
                value={selectedProject || ''}
                onChange={(e) => setSelectedProject(Number(e.target.value))}
                className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-slate-700 focus:outline-none focus:border-blue-500"
              >
                <option value="">Select a project</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Command</label>
              <TkTextarea
                value={command}
                onTkInput={(e: CustomEvent) => setCommand(e.detail.value)}
                placeholder="Enter your test command in natural language...

Example: Go to google.com, search for 'OpenAI', click the first result, and take a screenshot"
                rows={6}
                disabled={isExecuting}
              />
            </div>

            <div className="flex gap-3">
              <TkButton
                variant="primary"
                label={isExecuting ? 'Running...' : 'Run Test'}
                disabled={!selectedProject || !command.trim() || isExecuting}
                onClick={executeTest}
              />
              {isExecuting && (
                <TkButton
                  variant="secondary"
                  label="Cancel"
                  onClick={cancelTest}
                />
              )}
            </div>

            {/* Quick commands */}
            <div className="pt-4 border-t border-slate-200">
              <p className="text-sm text-slate-500 mb-2">Quick commands:</p>
              <div className="flex flex-wrap gap-2">
                {[
                  'Navigate to example.com and take a screenshot',
                  'Search Google for "test automation"',
                  'Fill the login form and submit',
                ].map((cmd, i) => (
                  <button
                    key={i}
                    onClick={() => setCommand(cmd)}
                    className="px-3 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg transition-colors"
                    disabled={isExecuting}
                  >
                    {cmd.slice(0, 30)}...
                  </button>
                ))}
              </div>
            </div>
          </div>
        </TkCard>

        {/* Output panel */}
        <TkCard>
          <div className="p-6 bg-white rounded-lg border border-slate-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-800">Execution Log</h3>
              {isExecuting && (
                <div className="flex items-center gap-2 text-sm text-blue-600">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  Running
                </div>
              )}
            </div>

            <div className="h-[500px] overflow-y-auto space-y-3 pr-2">
              {messages.length > 0 ? (
                messages.map((msg, index) => (
                  <div
                    key={index}
                    className="flex gap-3 p-3 bg-slate-50 rounded-lg animate-slide-up"
                  >
                    {getMessageIcon(msg.type)}
                    <div className="flex-1 min-w-0">
                      {renderMessageContent(msg)}
                      {msg.timestamp && (
                        <p className="text-xs text-slate-400 mt-1">
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </p>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500">
                  <div className="text-center">
                    <svg className="w-12 h-12 mx-auto mb-3 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p>Execution output will appear here</p>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </TkCard>
      </div>
    </div>
  );
}
