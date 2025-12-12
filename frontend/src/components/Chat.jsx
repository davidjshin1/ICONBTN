import { useState, useRef, useEffect } from 'react';
import imgUnGodlyLogo from '../assets/imgUnGodlyLogo.png';
import imgGroup41 from '../assets/imgGroup41.png';
import imgSend from '../assets/img.png';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [assets, setAssets] = useState([]);
  const [showGallery, setShowGallery] = useState(false);
  const messagesContainerRef = useRef(null);

  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    setMessages(prev => [...prev, { role: 'user', text: trimmed }]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Generation failed');
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        text: data.message,
        downloadUrl: data.download_url,
        assetType: data.asset_type
      }]);

      if (data.download_url) {
        setAssets(prev => [...prev, {
          url: data.download_url,
          type: data.asset_type,
          prompt: trimmed
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: `Error: ${error.message}`,
        isError: true
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white relative rounded-3xl w-full max-w-4xl h-[90vh] max-h-[800px] shadow-xl flex flex-col overflow-hidden">
      
      {/* Gallery Modal */}
      {showGallery && (
        <div className="absolute inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setShowGallery(false)}>
          <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b flex justify-between items-center shrink-0">
              <h2 className="text-lg font-semibold">Generated Assets ({assets.length})</h2>
              <button onClick={() => setShowGallery(false)} className="text-2xl text-gray-400 hover:text-black leading-none">&times;</button>
            </div>
            <div className="p-4 overflow-y-auto flex-1">
              {assets.length === 0 ? (
                <p className="text-gray-400 text-center py-8">No assets yet</p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {assets.map((asset, i) => (
                    <div key={i} className="border rounded-lg p-2 hover:shadow-md transition-shadow">
                      <div className="aspect-square bg-gray-50 rounded flex items-center justify-center mb-2 overflow-hidden">
                        <img src={asset.url} alt="" className="max-w-full max-h-full object-contain" />
                      </div>
                      <p className="text-xs text-gray-500 truncate">{asset.prompt}</p>
                      <a href={asset.url} download className="text-xs text-blue-600 hover:underline">Download</a>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Background Gradient */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-96 h-96 pointer-events-none opacity-30">
        <img src={imgGroup41} alt="" className="w-full h-full" />
      </div>

      {/* Header */}
      <div className="shrink-0 p-6 flex items-center justify-between border-b bg-white/80 backdrop-blur-sm relative z-10">
        <div className="flex items-center gap-3">
          <img src={imgUnGodlyLogo} alt="UNGODLY" className="h-8 w-auto" />
          <span className="text-[#160211] font-medium hidden sm:inline">UI Asset Generator</span>
        </div>
        <button
          onClick={() => setShowGallery(true)}
          className="px-3 py-1.5 bg-[#160211] text-white rounded-lg text-sm hover:bg-[#2a0420] transition-colors"
        >
          Gallery {assets.length > 0 && `(${assets.length})`}
        </button>
      </div>

      {/* Messages */}
      <div 
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth"
      >
        {messages.length === 0 && !isLoading ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-400 text-center px-4">
            <p className="text-lg mb-4">What would you like to create?</p>
            <div className="text-sm space-y-2 opacity-70">
              <p>"Give me a potion icon"</p>
              <p>"Create a primary CTA that says START"</p>
              <p>"Make a fire damage increased boon"</p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] sm:max-w-[70%] rounded-2xl ${
                  msg.role === 'user'
                    ? 'bg-[#160211] text-white p-3 rounded-br-sm'
                    : msg.isError
                      ? 'bg-red-50 text-red-600 border border-red-200 p-3 rounded-bl-sm'
                      : 'bg-gray-100 text-gray-800 p-3 rounded-bl-sm'
                }`}>
                  <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                  
                  {/* Image Preview */}
                  {msg.downloadUrl && (
                    <div className="mt-3 space-y-3">
                      <div className="bg-white rounded-lg p-2 border">
                        <img 
                          src={msg.downloadUrl} 
                          alt={msg.assetType}
                          className="max-w-full max-h-48 mx-auto object-contain rounded"
                        />
                      </div>
                      <a
                        href={msg.downloadUrl}
                        download
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-3 py-1.5 bg-[#160211] text-white text-sm rounded-lg hover:bg-[#2a0420] transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download {msg.assetType}
                      </a>
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {/* Loading indicator inline */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 text-gray-800 p-3 rounded-2xl rounded-bl-sm max-w-[85%] sm:max-w-[70%]">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></span>
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></span>
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></span>
                    </div>
                    <span className="text-sm text-gray-500">Generating your asset...</span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Input */}
      <div className="shrink-0 p-4 border-t bg-white/80 backdrop-blur-sm relative z-10">
        <div className="bg-white border border-gray-300 rounded-xl p-2 flex items-center gap-2 shadow-sm">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Create a UI asset..."
            disabled={isLoading}
            className="flex-1 outline-none text-sm text-gray-800 placeholder:text-gray-400 disabled:opacity-50 px-2"
          />
          <button
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
            className="w-8 h-8 flex-shrink-0 disabled:opacity-40 hover:opacity-80 transition-opacity"
          >
            <img src={imgSend} alt="Send" className="w-full h-full" />
          </button>
        </div>
      </div>
    </div>
  );
}
