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
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    // Add user message
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

      // Add assistant message
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: data.message,
        downloadUrl: data.download_url,
        assetType: data.asset_type
      }]);

      // Save to gallery
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
    <div className="bg-white overflow-hidden relative rounded-[32px] w-full max-w-[1327px] h-[900px] shadow-xl">
      
      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <div className="w-16 h-16 border-4 border-[#160211] border-t-transparent rounded-full animate-spin" />
            <p className="text-[#160211] text-lg font-medium">Generating...</p>
            <p className="text-gray-400 text-sm">This may take 10-30 seconds</p>
          </div>
        </div>
      )}

      {/* Gallery Modal */}
      {showGallery && (
        <div className="absolute inset-0 bg-black/60 z-50 flex items-center justify-center p-8" onClick={() => setShowGallery(false)}>
          <div className="bg-white rounded-2xl w-full max-w-3xl max-h-[80vh] overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold">Generated Assets ({assets.length})</h2>
              <button onClick={() => setShowGallery(false)} className="text-2xl text-gray-400 hover:text-black">&times;</button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              {assets.length === 0 ? (
                <p className="text-gray-400 text-center py-8">No assets yet. Generate something!</p>
              ) : (
                <div className="grid grid-cols-3 gap-4">
                  {assets.map((asset, i) => (
                    <div key={i} className="border rounded-lg p-2">
                      <div className="aspect-square bg-gray-50 rounded flex items-center justify-center mb-2">
                        <img src={asset.url} alt="" className="max-w-full max-h-full object-contain" />
                      </div>
                      <p className="text-xs text-gray-500 truncate mb-1">{asset.prompt}</p>
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
      <div className="absolute h-[464px] left-1/2 -translate-x-1/2 top-[501px] w-[544px] pointer-events-none opacity-50">
        <img src={imgGroup41} alt="" className="w-full h-full" />
      </div>

      {/* Gallery Button */}
      <button
        onClick={() => setShowGallery(true)}
        className="absolute top-6 right-6 px-4 py-2 bg-[#160211] text-white rounded-lg text-sm hover:bg-[#2a0420] z-10"
      >
        Gallery {assets.length > 0 && `(${assets.length})`}
      </button>

      {/* Logo */}
      <div className="absolute left-1/2 -translate-x-1/2 top-12 flex flex-col items-center gap-4">
        <img src={imgUnGodlyLogo} alt="UNGODLY" className="h-[50px] w-auto" />
        <p className="text-[#160211] text-2xl">UI Asset Generator</p>
      </div>

      {/* Messages */}
      <div className="absolute top-40 left-1/2 -translate-x-1/2 w-[883px] h-[500px] overflow-y-auto px-4">
        {messages.length === 0 && !isLoading ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-400">
            <p className="text-lg mb-4">What would you like to create?</p>
            <div className="text-sm space-y-2">
              <p>"Give me a potion icon"</p>
              <p>"Create a primary CTA that says START"</p>
              <p>"Make a fire damage increased boon"</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4 py-4">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[70%] p-4 rounded-2xl ${
                  msg.role === 'user'
                    ? 'bg-[#160211] text-white'
                    : msg.isError
                      ? 'bg-red-50 text-red-600 border border-red-200'
                      : 'bg-gray-100 text-gray-800'
                }`}>
                  <p className="text-sm">{msg.text}</p>
                  {msg.downloadUrl && (
                    <a
                      href={msg.downloadUrl}
                      download
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block mt-3 px-4 py-2 bg-[#160211] text-white text-sm rounded-lg hover:bg-[#2a0420]"
                    >
                      Download {msg.assetType}
                    </a>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 w-[883px]">
        <div className="bg-white border border-[rgba(22,2,17,0.3)] rounded-lg p-2.5 flex items-center gap-3 shadow-sm">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            placeholder="Create a UI asset..."
            disabled={isLoading}
            className="flex-1 outline-none text-sm text-gray-800 placeholder:text-gray-400 disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
            className="w-9 h-9 flex-shrink-0 disabled:opacity-40 hover:opacity-80"
          >
            <img src={imgSend} alt="Send" className="w-full h-full" />
          </button>
        </div>
      </div>
    </div>
  );
}
