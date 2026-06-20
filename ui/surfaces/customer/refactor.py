import re

with open('App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the giant render block
start_marker = r'\{/\* Dashboard Tab \*/\}'
end_marker = r'\{/\* Simulated SMS Notification Popup'

# Find the indices
start_match = re.search(start_marker, content)
end_match = re.search(end_marker, content)

start_idx = start_match.start()
end_idx = end_match.start()

replacement = """<React.Suspense fallback={<div className="flex justify-center items-center h-64 text-neutral-500 font-mono animate-pulse">Decrypting module payload...</div>}>
            {activeTab === 'dashboard' && <DashboardTab />}
            {activeTab === 'transfer' && <TransferTab />}
            {activeTab === 'beneficiaries' && <BeneficiariesTab />}
            {activeTab === 'statements' && <StatementsTab />}
            {activeTab === 'support' && <SupportTab />}
          </React.Suspense>

        </main>
      </div>

      {/* Simulated SMS Notification Popup"""

new_content = content[:start_idx] + replacement + content[end_idx + len('{/* Simulated SMS Notification Popup'):]

# Insert imports at the top
import_str = """
import { useAppContext } from './context/AppContext';
const DashboardTab = React.lazy(() => import('./pages/DashboardTab'));
const TransferTab = React.lazy(() => import('./pages/TransferTab'));
const BeneficiariesTab = React.lazy(() => import('./pages/BeneficiariesTab'));
const StatementsTab = React.lazy(() => import('./pages/StatementsTab'));
const SupportTab = React.lazy(() => import('./pages/SupportTab'));
"""

new_content = new_content.replace("import digitalBankingImg", import_str + "\nimport digitalBankingImg")

with open('App.tsx', 'w', encoding='utf-8') as f:
    f.write(new_content)
