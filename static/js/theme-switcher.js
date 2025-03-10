document.addEventListener('DOMContentLoaded', function() {
    // Get theme switch button and theme icon
    const themeSwitch = document.getElementById('themeSwitch');
    const themeSwitchIcon = themeSwitch ? themeSwitch.querySelector('i') : null;
    
    // Function to set theme
    function setTheme(theme) {
        // Add transition class if not already present
        if (!document.body.classList.contains('theme-transition')) {
            document.body.classList.add('theme-transition');
        }
        
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        
        // Update icon and text based on current theme
        if (themeSwitchIcon && themeSwitch) {
            if (theme === 'dark') {
                themeSwitchIcon.classList.remove('fa-moon');
                themeSwitchIcon.classList.add('fa-sun');
                themeSwitch.innerHTML = '<i class="fas fa-sun"></i> Light Mode';
            } else {
                themeSwitchIcon.classList.remove('fa-sun');
                themeSwitchIcon.classList.add('fa-moon');
                themeSwitch.innerHTML = '<i class="fas fa-moon"></i> Dark Mode';
            }
        }
    }
    
    // Check for saved theme preference or respect OS setting
    const savedTheme = localStorage.getItem('theme');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Apply theme (this will just ensure the UI is synced)
    if (savedTheme) {
        setTheme(savedTheme);
    } else if (prefersDarkScheme) {
        setTheme('dark');
    } else {
        setTheme('light');
    }
    
    // Toggle theme on click
    if (themeSwitch) {
        themeSwitch.addEventListener('click', function(e) {
            e.preventDefault();
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            setTheme(newTheme);
        });
    }
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        // Only apply if no theme preference is saved
        if (!localStorage.getItem('theme')) {
            const newTheme = e.matches ? 'dark' : 'light';
            setTheme(newTheme);
        }
    });
});
