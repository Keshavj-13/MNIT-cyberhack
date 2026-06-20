import re

with open('App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace local states in App.tsx with useAppContext
# Find "export default function App() {" and the end of states
start_marker = "export default function App() {"
end_marker = "  // Registration / Sign-up state"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

replacement = """export default function App() {
  const pref = usePreferences();
  const t = (key: string) => T[pref.lang][key] || key;

  const { 
    cryptoState, isAuthenticated, setIsAuthenticated, username, 
    keyRotationInfo, showCryptoModal, setShowCryptoModal, keyRotatedAnim,
    refreshData 
  } = useAppContext();

  // Navigation UI state
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
"""

new_content = content[:start_idx] + replacement + content[end_idx:]

with open('App.tsx', 'w', encoding='utf-8') as f:
    f.write(new_content)
