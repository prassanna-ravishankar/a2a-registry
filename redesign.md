## **A2A Cortex UI Design Guide: Cyber-Industrial Terminal**

This guide documents the design principles and technical specifications for the "A2A Cortex" user interface, characterized by a high-contrast, dense, and functional aesthetic reminiscent of a command line interface (CLI) or a system monitoring utility.

### **1\. Design Philosophy: The Command Center**

The goal is to create an environment that feels authoritative, data-rich, and non-distracting.

* **Cyber-Industrial Aesthetics:** Utilize high-contrast dark backgrounds, neon-accent colors, and structured grid layouts.  
* **Data Density:** Prioritize showing maximum information without clutter. Use small, legible typefaces and borders to create visual separation.  
* **Monospaced Focus:** Employ monospaced fonts (like *Fira Code* or *IBM Plex Mono*, simulated here by Tailwind's font-mono) to emphasize technical precision and data alignment.  
* **Interactivity:** Use subtle hover effects (e.g., color shift, simulated "glitch") to indicate functional elements.

### **2\. Color Palette & Usage**

The palette is extremely limited, relying on high contrast to define hierarchy.

| Color Name | Hex Code | Tailwind Class | Usage Context |
| :---- | :---- | :---- | :---- |
| **Primary Background** | \#000000 | bg-black | Core background for main panels. |
| **Secondary Background** | \#0a0a0a | bg-zinc-950 | Structural elements (Header, Sidebar, Inspection Deck). |
| **Border/Divider** | \#27272a | border-zinc-800 | All major panel dividers, element separators. |
| **Primary Accent (Active/Success)** | \#10b981 | text-emerald-500 | System status (Online), active links, primary buttons. |
| **Warning/Attention** | \#f59e0b | text-amber-500 | Agent status (Warning), system alerts. |
| **Error/Offline** | \#ef4444 | text-red-500 | Agent status (Offline), critical errors. |
| **Primary Text** | \#e4e4e7 | text-zinc-200 | Headings, essential data. |
| **Secondary Text** | \#71717a | text-zinc-500 | Labels, timestamps, metadata, disabled states. |
| **Tertiary Background** | \#18181b | bg-zinc-900 | Selected states, code blocks, input fields. |

### **3\. Typography**

Monospaced fonts are mandatory for the application's atmosphere.

* **Font Family:** font-mono (Simulates a system/terminal font like Fira Code or IBM Plex Mono)  
* **Base Size:** text-sm (14px) for general content.  
* **Data/Utility Text:** text-xs (12px) and text-\[10px\] for labels, tags, timestamps, and console logs.  
* **Headings:** Use bold weight (font-bold) and tracking (tracking-wider, tracking-widest) to simulate command headers.

### **4\. Layout & Structure**

The design follows a strict, non-scrolling, three-column layout. Scrolling is confined to internal panels.

| Panel | Width | Function | Key Features |
| :---- | :---- | :---- | :---- |
| **Left Sidebar** | w-64 | **Telemetry & Filters** | Fixed width. Filters list and a streaming, chronological "Live Feed." Includes a bottom metric bar (CPU\_LOAD). |
| **Center Main** | flex-1 | **Agent Grid / Manifest** | Fluid width, scrollable content. Utilizes a sparse, tiled background grid (bg-\[linear-gradient...\]). Responsive (1-2 columns). |
| **Right Sidebar** | w-\[450px\] | **Inspection Deck** | Fixed width. Displays detailed information, connection interface, and command terminal for the selected agent. |
| **Header** | h-12 | **Global Navigation** | Fixed height. Contains system status, application title, and global search. |

### **5\. Component Style Guide**

#### **5.1 Agent Card (Center Panel)**

* **Structure:** Relative container with absolute corner markers for a "framed" effect.  
* **Border State:** Uses conditional logic:  
  * **Inactive:** border-zinc-800, bg-zinc-950  
  * **Active (Selected):** border-emerald-500/50, bg-zinc-900/80, subtle shadow (shadow-\[0\_0\_20px\_rgba(16,185,129,0.1)\]).  
* **Glitch Effect (GlitchText):** Simulates transmission interference on the agent name upon hover using positioned cyan and red text overlays with low opacity and slight offsets.

#### **5.2 Terminal Input / Output**

* **Log Line (TerminalLine):** Uses a fixed format: \[TIME\] \<TYPE\> CONTENT.  
  * **Request (\>\>):** Cyan text (text-cyan-400).  
  * **Response (\<\<):** Emerald text (text-emerald-400).  
  * **System (\!\!):** Amber text (text-amber-400).  
* **Input Field:** Transparent background, no border, uses a pulsing underscore (\_) as a custom cursor, set to text-emerald-500 for high visibility.

#### **5.3 Buttons & Interactive Elements**

* **Primary Action (Connect):** High-impact, high-contrast. bg-emerald-600 on hover, text-black, uppercase, bold.  
* **Secondary Action (Docs):** Border-based, low-key. border-zinc-700, text-zinc-300, uppercase, hover changes border color.  
* **Tabs:** Bordered at the bottom. Active state uses border-emerald-500, text-emerald-500, and a subtle bg-emerald-500/5 background fill.