import { useState, useEffect, useRef } from 'react';
import { apiClient } from '@/api/client';
import { Project, TestRun, WSMessage } from '@/types';

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
      const testRun = await apiClient.executeTest(selectedProject, command) as TestRun;
      setCurrentTestRun(testRun);

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
          data: { error: 'WebSocket stream connection error' }
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
        data: { error: error instanceof Error ? error.message : 'Failed to initialize test run' }
      }]);
    }
  };

  const cancelTest = () => {
    if (currentTestRun) {
      wsRef.current?.send(JSON.stringify({ action: 'cancel' }));
    }
  };

  const getMessageBadge = (type: string) => {
    switch (type) {
      case 'status':
        return <span className="px-2 py-0.5 text-[10px] font-mono font-semibold rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">INFO</span>;
      case 'tool_call':
        return <span className="px-2 py-0.5 text-[10px] font-mono font-semibold rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">TOOL</span>;
      case 'tool_result':
        return <span className="px-2 py-0.5 text-[10px] font-mono font-semibold rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">RESULT</span>;
      case 'llm_response':
        return <span className="px-2 py-0.5 text-[10px] font-mono font-semibold rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">AI RESP</span>;
      case 'complete':
        return <span className="px-2 py-0.5 text-[10px] font-mono font-semibold rounded bg-emerald-500/30 text-emerald-300 border border-emerald-400/40">SUCCESS</span>;
      case 'error':
        return <span className="px-2 py-0.5 text-[10px] font-mono font-semibold rounded bg-red-500/20 text-red-400 border border-red-500/30">ERROR</span>;
      default:
        return <span className="px-2 py-0.5 text-[10px] font-mono font-semibold rounded bg-slate-800 text-slate-400">EVENT</span>;
    }
  };

  const renderMessageContent = (msg: WSMessage) => {
    const data = msg.data;
    
    switch (msg.type) {
      case 'status':
        return <p className="text-slate-300 font-mono text-xs">{data.message as string}</p>;
      
      case 'tool_call':
        return (
          <div>
            <p className="text-purple-400 font-mono font-semibold text-xs">{data.tool_name as string}</p>
            <pre className="mt-1.5 p-2 bg-slate-950 rounded-lg text-xs font-mono text-slate-300 border border-slate-800 overflow-x-auto">
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
            <p className={`font-mono text-xs font-semibold ${result.success ? 'text-emerald-400' : 'text-red-400'}`}>
              {data.tool_name as string}: {result.success ? 'PASS' : 'FAIL'}
            </p>
            {resultDataStr && (
              <pre className="mt-1.5 p-2 bg-slate-950 rounded-lg text-xs font-mono text-slate-300 border border-slate-800 max-h-40 overflow-y-auto">
                {resultDataStr}
              </pre>
            )}
            {result.error && (
              <p className="mt-1 text-xs font-mono text-red-400">{result.error}</p>
            )}
          </div>
        );
      
      case 'llm_response':
        return <p className="text-slate-200 font-mono text-xs whitespace-pre-wrap">{data.content as string}</p>;
      
      case 'complete':
        return <p className="text-emerald-400 font-mono font-semibold text-xs">{data.message as string}</p>;
      
      case 'error':
        return <p className="text-red-400 font-mono text-xs">{data.error as string}</p>;
      
      default:
        return <pre className="text-xs font-mono text-slate-400">{JSON.stringify(data, null, 2)}</pre>;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header Banner */}
      <div className="p-6 glass-card rounded-2xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">AI Test Execution Terminal</h1>
          <p className="text-slate-400 text-xs font-mono mt-1">Run natural language browser automation powered by vLLM agent</p>
        </div>
        {isExecuting && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
            Executing Test Run #{currentTestRun?.id}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Command Prompt Form Panel */}
        <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-5">
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">Target Workspace Project</label>
            <select
              value={selectedProject || ''}
              onChange={(e) => setSelectedProject(Number(e.target.value))}
              className="w-full px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 text-xs font-mono focus:outline-none focus:border-cyan-500"
            >
              <option value="">Select Target Project</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">AI Natural Language Prompt</label>
            <textarea
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder={`Enter test steps in plain text...\n\nExample: Go to google.com, search for 'vLLM agent browser', click the top result and verify navigation.`}
              rows={6}
              disabled={isExecuting}
              className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono text-xs leading-relaxed"
            />
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              disabled={!selectedProject || !command.trim() || isExecuting}
              onClick={executeTest}
              className="flex-1 py-3 px-4 bg-gradient-to-r from-blue-600 via-cyan-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 disabled:opacity-40 text-white rounded-xl font-semibold text-xs shadow-lg shadow-cyan-500/20 transition-all flex items-center justify-center gap-2 font-mono"
            >
              {isExecuting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Executing...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  </svg>
                  Run Agent Test
                </>
              )}
            </button>
            {isExecuting && (
              <button
                onClick={cancelTest}
                className="py-3 px-4 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 rounded-xl font-mono text-xs font-semibold transition-all"
              >
                Abort
              </button>
            )}
          </div>

          {/* Quick Preset Prompt Snippets */}
          <div className="pt-4 border-t border-slate-800/80">
            <p className="text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-2.5">Preset Test Prompts:</p>
            <div className="space-y-2">
              {[
                'Navigate to https://example.com and check main header title',
                'Go to google.com, search for "vLLM agent browser" and capture screenshot',
                'Check login form inputs and verify validation errors',
              ].map((cmd, i) => (
                <button
                  key={i}
                  onClick={() => setCommand(cmd)}
                  disabled={isExecuting}
                  className="w-full text-left p-2.5 bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/30 rounded-xl text-xs font-mono text-slate-300 transition-all truncate block"
                >
                  ⚡ {cmd}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Real-time Execution Log Terminal Panel */}
        <div className="glass-card p-6 rounded-2xl border border-slate-800 flex flex-col h-[560px]">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block"></span>
              <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block"></span>
              <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block"></span>
              <span className="ml-2 text-xs font-mono text-slate-400">ws://live-execution-feed</span>
            </div>
            {isExecuting && (
              <span className="text-[10px] font-mono text-cyan-400 animate-pulse">STREAMING LIVE</span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 pr-2 font-mono">
            {messages.length > 0 ? (
              messages.map((msg, index) => (
                <div
                  key={index}
                  className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/80 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    {getMessageBadge(msg.type)}
                    {msg.timestamp && (
                      <span className="text-[10px] font-mono text-slate-500">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                  <div className="pt-1">
                    {renderMessageContent(msg)}
                  </div>
                </div>
              ))
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 font-mono text-xs">
                <div className="text-center space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-600">
                    &gt;_
                  </div>
                  <p>Awaiting test execution trigger...</p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}
