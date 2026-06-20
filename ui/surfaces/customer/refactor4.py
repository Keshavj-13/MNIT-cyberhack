import re

with open('App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the missing setters from handleLogout
missing_setters = [
    r"\s*setTransferStatus\(null\);",
    r"\s*setTransferAmount\(''\);",
    r"\s*setSelectedBeneficiaryId\(''\);",
    r"\s*setSimulatedSmsCode\(null\);",
    r"\s*setSmsNotification\(null\);",
    r"\s*setShowOtpModal\(false\);"
]

for setter in missing_setters:
    content = re.sub(setter, "", content)

with open('App.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
