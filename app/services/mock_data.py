"""Mock data service for development and testing."""

import uuid
from datetime import datetime, timedelta
from typing import List
import random

from app.models.schemas import SolutionRecord
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# Sample IT solutions for testing
SAMPLE_SOLUTIONS = [
    {
        "title": "Password Reset Procedure",
        "category": "Authentication",
        "content": """Step-by-step guide for IT staff to reset user passwords:

1. Verify user identity through secondary authentication
2. Access Active Directory Users and Computers console
3. Navigate to the user account in question
4. Right-click the account and select 'Reset Password'
5. Generate a temporary secure password
6. Set 'User must change password at next logon'
7. Communicate the temporary password securely to the user
8. Document the password reset in the ticketing system

Important: Always follow company security policies and ensure proper documentation.""",
        "tags": ["password", "authentication", "active-directory", "security"]
    },
    {
        "title": "Printer Connectivity Issues",
        "category": "Hardware",
        "content": """Troubleshooting guide for printer connectivity problems:

1. Check physical connections (USB/Ethernet cables)
2. Verify printer power status and display messages
3. Test network connectivity if using network printer
4. Check printer driver installation and version
5. Clear print queue and restart print spooler service
6. Verify printer sharing settings if applicable
7. Test with different user account to isolate permission issues
8. Consider IP address conflicts for network printers

Advanced: Use PING and TELNET to test network printer connectivity.""",
        "tags": ["printer", "hardware", "connectivity", "network", "troubleshooting"]
    },
    {
        "title": "VPN Connection Problems",
        "category": "Network",
        "content": """IT staff guide for resolving VPN connection issues:

1. Verify user credentials and account status
2. Check VPN client software version and updates
3. Confirm firewall and antivirus software exceptions
4. Test internet connectivity without VPN
5. Verify VPN server address and port settings
6. Check for conflicting network adapters
7. Review Windows Event Logs for VPN-related errors
8. Test alternative VPN protocols if available
9. Consider certificate issues for SSL VPNs

Escalation: Contact network team for server-side issues.""",
        "tags": ["vpn", "network", "connectivity", "remote-access", "firewall"]
    },
    {
        "title": "Email Client Configuration",
        "category": "Email",
        "content": """Setting up email clients for end users:

Outlook Configuration:
1. Open Outlook and go to File > Add Account
2. Enter user's email address
3. Use Auto Account Setup when possible
4. Manual setup if needed:
   - IMAP: server.company.com, port 993, SSL
   - SMTP: smtp.company.com, port 587, TLS
5. Test send and receive functionality
6. Configure calendar and contacts sync if applicable

Mobile Device Setup:
- Use Exchange ActiveSync settings
- Server: mail.company.com
- Domain: company.com (if required)
- Enable SSL/TLS encryption""",
        "tags": ["email", "outlook", "exchange", "mobile", "configuration"]
    },
    {
        "title": "Software Installation Issues",
        "category": "Software",
        "content": """Resolving software installation problems:

Pre-installation checks:
1. Verify system requirements and compatibility
2. Check available disk space
3. Ensure administrative privileges
4. Disable antivirus temporarily if needed

Common installation failures:
1. Missing .NET Framework or Visual C++ redistributables
2. Previous installation remnants - use removal tools
3. Windows Installer service issues - restart service
4. Registry conflicts - backup before making changes
5. Group Policy restrictions - verify software allowlists

Post-installation:
- Test application functionality
- Configure user permissions and shortcuts
- Update software to latest version""",
        "tags": ["software", "installation", "windows", "compatibility", "troubleshooting"]
    },
    {
        "title": "Network Drive Mapping",
        "category": "Network",
        "content": """IT guide for mapping network drives:

Windows Method:
1. Open File Explorer
2. Click 'This PC' then 'Map network drive'
3. Select drive letter and enter UNC path (\\\\server\\share)
4. Check 'Reconnect at sign-in' for persistence
5. Enter credentials if prompted
6. Test access and permissions

Group Policy Method:
1. Open Group Policy Management Console
2. Navigate to User Configuration > Preferences > Drive Maps
3. Create new mapped drive
4. Specify target path, label, and drive letter
5. Configure security filtering as needed

Troubleshooting:
- Verify server and share accessibility
- Check user permissions on target folder
- Test with different user account""",
        "tags": ["network-drive", "file-sharing", "group-policy", "permissions", "windows"]
    },
    {
        "title": "Blue Screen of Death (BSOD) Analysis",
        "category": "Hardware",
        "content": """Analyzing and resolving BSOD errors for IT staff:

Initial Response:
1. Note the STOP code and any driver names
2. Check if system restarts automatically
3. Document frequency and circumstances of BSODs

Analysis Steps:
1. Use Windows Memory Diagnostic to test RAM
2. Check Event Viewer for critical errors
3. Use BlueScreenView or WinDbg for dump analysis
4. Identify problematic drivers or hardware
5. Check for overheating issues

Common Causes:
- Faulty RAM modules
- Outdated or corrupted drivers
- Hardware compatibility issues
- Overheating CPU/GPU
- Power supply problems

Resolution:
- Update drivers and Windows
- Run hardware diagnostics
- Replace faulty components
- Check system cooling""",
        "tags": ["bsod", "hardware", "diagnostics", "drivers", "memory", "troubleshooting"]
    },
    {
        "title": "Active Directory Account Management",
        "category": "Authentication",
        "content": """Managing user accounts in Active Directory:

Creating New Users:
1. Open Active Directory Users and Computers
2. Navigate to appropriate OU
3. Right-click > New > User
4. Enter user details and logon name
5. Set password and account options
6. Add to appropriate security groups
7. Configure profile path and home folder

Account Modifications:
- Disable/Enable accounts as needed
- Password resets with force change option
- Group membership management
- Attribute updates (phone, department, etc.)

Bulk Operations:
- Use PowerShell for multiple account changes
- Import users from CSV files
- Automated provisioning scripts

Security Best Practices:
- Follow least privilege principle
- Regular account auditing
- Implement strong password policies""",
        "tags": ["active-directory", "user-management", "security", "powershell", "authentication"]
    },
    {
        "title": "Backup and Recovery Procedures",
        "category": "Data Management",
        "content": """IT staff guide for data backup and recovery:

Daily Backup Checks:
1. Verify backup job completion status
2. Check backup logs for errors or warnings
3. Test random file restoration
4. Monitor backup storage capacity
5. Document any failures or issues

Recovery Procedures:
1. Assess data loss scope and urgency
2. Identify most recent clean backup
3. Prepare recovery environment
4. Restore data incrementally if possible
5. Verify data integrity after restoration
6. Test application functionality
7. Document recovery process and timeline

Best Practices:
- Follow 3-2-1 backup rule
- Test recovery procedures regularly
- Maintain offsite backup copies
- Encrypt sensitive backup data
- Train users on data protection""",
        "tags": ["backup", "recovery", "data-management", "disaster-recovery", "storage"]
    },
    {
        "title": "Wireless Network Troubleshooting",
        "category": "Network",
        "content": """Resolving WiFi connectivity issues:

Signal and Connection Issues:
1. Check signal strength and interference
2. Test with different devices in same location
3. Verify wireless adapter drivers and settings
4. Scan for channel conflicts with WiFi analyzer
5. Check access point power and antenna orientation

Authentication Problems:
1. Verify network password and security type
2. Check MAC address filtering if enabled
3. Review wireless client limits on access point
4. Test with different user credentials
5. Check certificate issues for enterprise networks

Performance Issues:
1. Test bandwidth with speed testing tools
2. Check for network congestion during peak hours
3. Verify QoS settings and traffic shaping
4. Consider upgrading to newer WiFi standards
5. Optimize access point placement and configuration

Advanced Troubleshooting:
- Use packet capture tools for detailed analysis
- Check DHCP scope and IP address conflicts
- Review wireless controller logs and settings""",
        "tags": ["wifi", "wireless", "network", "connectivity", "troubleshooting", "performance"]
    }
]


class MockDataService:
    """Service for generating mock SolarWinds solution data."""
    
    def __init__(self):
        self.solutions_generated = False
        
    def generate_mock_solutions(self) -> List[SolutionRecord]:
        """Generate mock solution records for development."""
        solutions = []
        
        # Use base solutions and create variations
        base_count = len(SAMPLE_SOLUTIONS)
        target_count = settings.mock_solutions_count
        
        for i in range(target_count):
            # Cycle through base solutions and create variations
            base_solution = SAMPLE_SOLUTIONS[i % base_count]
            
            # Generate unique ID
            solution_id = f"mock-solution-{i+1:03d}"
            
            # Add variation to title if we're repeating
            title = base_solution["title"]
            if i >= base_count:
                variation = (i // base_count) + 1
                title = f"{title} (Variation {variation})"
            
            # Create random updated timestamp within last 30 days
            days_ago = random.randint(0, 30)
            updated_at = datetime.utcnow() - timedelta(days=days_ago)
            
            # Create solution record
            solution = SolutionRecord(
                id=solution_id,
                title=title,
                category=base_solution["category"],
                content=base_solution["content"],
                updated_at=updated_at,
                tags=base_solution["tags"].copy(),
                url=f"https://mock.solarwinds.com/kb/{solution_id}"
            )
            
            solutions.append(solution)
        
        logger.info(f"Generated {len(solutions)} mock solutions for development")
        self.solutions_generated = True
        
        return solutions
    
    def get_random_solutions(self, count: int = 5) -> List[SolutionRecord]:
        """Get a random subset of mock solutions."""
        all_solutions = self.generate_mock_solutions()
        return random.sample(all_solutions, min(count, len(all_solutions)))
    
    def is_mock_mode_enabled(self) -> bool:
        """Check if mock data mode is enabled."""
        return (
            settings.enable_mock_data and 
            (not settings.solarwinds_api_key or not settings.solarwinds_base_url)
        )


# Global service instance
mock_data_service = MockDataService()