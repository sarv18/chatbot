import { useState, useRef, useEffect } from "react";
import { API_BASE_URL } from "../config";

interface ChatProps {
  conversationId?: string;
  systemPrompt?: string;
}

export default function Chat({ conversationId, systemPrompt }: ChatProps) {
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([
    { role: "assistant", content: "Hello! How can I help you today?" },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const convId = useRef(conversationId || `conv_${Date.now()}`);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/v1/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": "local-dev-key",
        },
        body: JSON.stringify({
          message: trimmed,
          conversation_id: convId.current,
          index_name: "local-kb",
          system_prompt: systemPrompt || "You are a helpful assistant.",
          stream: false,
        }),
      });

      const data = await response.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.message || "I don't know." }]);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I'm having trouble connecting. Please try again." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "20px" }}>
      <h1 style={{ textAlign: "center" }}>Support Chat</h1>

      <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "20px", minHeight: "300px", maxHeight: "400px", overflowY: "auto" }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ marginBottom: "16px", textAlign: msg.role === "user" ? "right" : "left" }}>
            <div
              style={{
                display: "inline-block",
                padding: "12px 16px",
                borderRadius: "12px",
                background: msg.role === "user" ? "#007bff" : "#f0f0f0",
                color: msg.role === "user" ? "white" : "black",
                maxWidth: "80%",
                textAlign: "left",
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div style={{ display: "flex", gap: "8px", marginTop: "16px" }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Type your message..."
          style={{ flex: 1, padding: "12px", border: "1px solid #ddd", borderRadius: "4px" }}
        />
        <button
          onClick={sendMessage}
          disabled={isLoading}
          style={{ padding: "12px 24px", background: "#007bff", color: "white", border: "none", borderRadius: "4px", cursor: isLoading ? "not-allowed" : "pointer" }}
        >
          {isLoading ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}