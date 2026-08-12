import Link from "next/link";

export default function WorkspacePage() {
  return (
    <div className="h-full w-full overflow-hidden bg-background font-interface-sm text-interface-sm text-on-surface antialiased flex flex-col min-h-screen">
      
      {/* TopNavBar */}
      <header className="flex justify-between items-center h-16 px-page-margin w-full sticky top-0 z-50 bg-surface border-b border-outline-variant">
        <div className="flex items-center gap-4">
          <Link href="/library" className="text-on-surface-variant hover:text-primary transition-colors flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 0, 'wght' 300" }}>arrow_back</span>
            <span>Library</span>
          </Link>
          <div className="h-4 w-px bg-outline-variant"></div>
          <h1 className="font-headline-md text-headline-md font-bold text-primary">Designing Data-Intensive Applications</h1>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-4">
            <button className="text-on-surface-variant hover:text-primary transition-colors">
              <span className="material-symbols-outlined">notifications</span>
            </button>
            <button className="text-on-surface-variant hover:text-primary transition-colors">
              <span className="material-symbols-outlined">settings</span>
            </button>
            <div className="w-8 h-8 rounded-full overflow-hidden border border-outline-variant cursor-pointer">
              <img alt="User avatar" className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDmaT2h00YG0HB46mQ0ghxLuOT6OPuQgLpiHRHJzaYoUOiB2cUOovDr8Bs846646G7_G-NMyguo4i42im-8Qzinioie1yjyD72hwm5IovdIaLj1bFLyI68K2_8aZOIs58Mg5_FfMlUgBSw7FdwYQ4heOIgn0ISby7Edjt0ibbTV2avVpQDuLEiVLuSYhqtWWPyFfMqp0XQJ38qn-CFFXwsX_rydIXPFYXk3HE3SWS4N4-GkWqMdGK8B" />
            </div>
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="flex-1 flex overflow-hidden w-full relative h-[calc(100vh-64px)]">
        
        {/* Left Sidebar (SideNavBar) */}
        <aside className="flex flex-col h-full sticky left-0 py-element-gap gap-control-padding bg-surface-container-lowest border-r border-outline-variant w-70 shrink-0">
          <div className="px-4 mb-4">
            <h2 className="font-interface-sm text-interface-sm text-on-surface-variant mb-1">Current Document</h2>
            <p className="text-xs text-on-surface-variant opacity-70">Designing Data-Intensive...</p>
          </div>
          
          <div className="flex px-2 gap-1 mb-4">
            <button className="flex-1 flex flex-col items-center p-2 text-primary font-bold bg-surface-container rounded-xl cursor-pointer active:scale-[0.98]">
              <span className="material-symbols-outlined text-[20px] mb-1">menu_book</span>
              <span className="text-[10px]">Contents</span>
            </button>
            <button className="flex-1 flex flex-col items-center p-2 text-on-surface-variant hover:bg-surface-container-low transition-all rounded-xl cursor-pointer active:scale-[0.98]">
              <span className="material-symbols-outlined text-[20px] mb-1">description</span>
              <span className="text-[10px]">Notes</span>
            </button>
            <button className="flex-1 flex flex-col items-center p-2 text-on-surface-variant hover:bg-surface-container-low transition-all rounded-xl cursor-pointer active:scale-[0.98]">
              <span className="material-symbols-outlined text-[20px] mb-1">stylus</span>
              <span className="text-[10px]">Highlights</span>
            </button>
            <button className="flex-1 flex flex-col items-center p-2 text-on-surface-variant hover:bg-surface-container-low transition-all rounded-xl cursor-pointer active:scale-[0.98]">
              <span className="material-symbols-outlined text-[20px] mb-1">bookmark</span>
              <span className="text-[10px]">Bookmarks</span>
            </button>
          </div>

          {/* Contents Hierarchy */}
          <div className="flex-1 overflow-y-auto px-4">
            <ul className="space-y-1">
              <li>
                <div className="flex justify-between items-center py-1.5 px-2 hover:bg-surface-container-low rounded-md cursor-pointer text-on-surface-variant">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                    <span>Chapter 4: Encoding</span>
                  </div>
                  <span className="text-xs opacity-50">111</span>
                </div>
              </li>
              <li>
                <div className="flex justify-between items-center py-1.5 px-2 bg-surface-container rounded-md cursor-pointer text-primary font-bold">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-[16px]">expand_more</span>
                    <span>Chapter 5: Replication</span>
                  </div>
                  <span className="text-xs opacity-50">151</span>
                </div>
                <ul className="pl-6 mt-1 space-y-1 border-l ml-4 border-outline-variant/30">
                  <li>
                    <div className="flex justify-between items-center py-1 px-2 hover:bg-surface-container-low rounded-md cursor-pointer text-on-surface-variant text-sm">
                      <span>Leaders and Followers</span>
                      <span className="text-xs opacity-50">152</span>
                    </div>
                  </li>
                  <li>
                    <div className="flex justify-between items-center py-1 px-2 hover:bg-surface-container-low rounded-md cursor-pointer text-on-surface-variant text-sm">
                      <span>Synchronous vs Asynchronous</span>
                      <span className="text-xs opacity-50">153</span>
                    </div>
                  </li>
                  <li>
                    <div className="flex justify-between items-center py-1 px-2 bg-primary/5 rounded-md cursor-pointer text-primary font-medium text-sm">
                      <span>Setting Up New Followers</span>
                      <span className="text-xs opacity-50">155</span>
                    </div>
                  </li>
                  <li>
                    <div className="flex justify-between items-center py-1 px-2 hover:bg-surface-container-low rounded-md cursor-pointer text-on-surface-variant text-sm">
                      <span>Handling Node Outages</span>
                      <span className="text-xs opacity-50">156</span>
                    </div>
                  </li>
                </ul>
              </li>
              <li>
                <div className="flex justify-between items-center py-1.5 px-2 hover:bg-surface-container-low rounded-md cursor-pointer text-on-surface-variant">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                    <span>Chapter 6: Partitioning</span>
                  </div>
                  <span className="text-xs opacity-50">199</span>
                </div>
              </li>
            </ul>
          </div>
          
          <div className="mt-auto pt-4 px-2 border-t border-outline-variant">
            <button className="flex w-full items-center gap-3 px-4 py-2 text-on-surface-variant hover:bg-surface-container-low rounded-md transition-colors">
              <span className="material-symbols-outlined text-[20px]">help</span>
              <span>Help</span>
            </button>
            <button className="flex w-full items-center gap-3 px-4 py-2 text-on-surface-variant hover:bg-surface-container-low rounded-md transition-colors">
              <span className="material-symbols-outlined text-[20px]">chevron_left</span>
              <span>Collapse</span>
            </button>
          </div>
        </aside>

        {/* Center Canvas (Document Viewer) */}
        <section className="flex-1 bg-surface-dim relative overflow-hidden flex flex-col">
          
          {/* Floating Reader Toolbar */}
          <div className="absolute top-6 left-1/2 -translate-x-1/2 z-10 flex items-center bg-surface-container-lowest border border-outline-variant rounded-full shadow-[0_10px_30px_rgba(0,0,0,0.08)] px-2 py-1.5 gap-2">
            <div className="flex items-center bg-surface-container-low rounded-full p-1 gap-1">
              <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-lowest transition-colors"><span className="material-symbols-outlined text-[18px]">article</span></button>
              <button className="w-8 h-8 rounded-full flex items-center justify-center bg-surface-container-lowest text-primary shadow-sm"><span className="material-symbols-outlined text-[18px]">menu_book</span></button>
              <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-lowest transition-colors"><span className="material-symbols-outlined text-[18px]">view_agenda</span></button>
            </div>
            <div className="w-px h-6 bg-outline-variant mx-1"></div>
            <div className="flex items-center gap-1">
              <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low transition-colors"><span className="material-symbols-outlined text-[18px]">remove</span></button>
              <span className="text-xs font-medium w-10 text-center">100%</span>
              <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low transition-colors"><span className="material-symbols-outlined text-[18px]">add</span></button>
            </div>
            <div className="w-px h-6 bg-outline-variant mx-1"></div>
            <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low transition-colors" title="Focus Mode"><span className="material-symbols-outlined text-[18px]">fullscreen</span></button>
          </div>

          {/* Vertical Annotation Toolbar */}
          <div className="absolute left-6 top-1/2 -translate-y-1/2 z-10 flex flex-col bg-surface-container-lowest border border-outline-variant rounded-full shadow-[0_10px_30px_rgba(0,0,0,0.08)] p-1.5 gap-1">
            <button className="w-8 h-8 rounded-full flex items-center justify-center bg-primary/10 text-primary"><span className="material-symbols-outlined text-[18px]">arrow_selector_tool</span></button>
            <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low transition-colors"><span className="material-symbols-outlined text-[18px]">pan_tool</span></button>
            <div className="w-6 h-px bg-outline-variant mx-auto my-1"></div>
            <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low transition-colors"><span className="material-symbols-outlined text-[18px]">draw</span></button>
            <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low transition-colors"><span className="material-symbols-outlined text-[18px]">format_ink_highlighter</span></button>
            <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low transition-colors"><span className="material-symbols-outlined text-[18px]">match_case</span></button>
            <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low transition-colors"><span className="material-symbols-outlined text-[18px]">arrow_forward</span></button>
            <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low transition-colors"><span className="material-symbols-outlined text-[18px]">category</span></button>
          </div>

          {/* Document Pages Container */}
          <div className="flex-1 overflow-auto p-12 flex justify-center items-start gap-4">
            
            {/* Page 162 */}
            <div className="w-125 min-h-187.5 bg-white shadow-[0_4px_20px_rgba(0,0,0,0.04)] flex flex-col relative shrink-0">
              <div className="flex-1 p-10 font-reading-body text-reading-body text-on-background relative">
                <div className="text-[10px] text-on-surface-variant uppercase tracking-wider mb-8 text-center font-interface-sm">162</div>
                <h3 className="font-bold text-xl mb-4">Setting Up New Followers</h3>
                <p className="mb-4 text-justify">From time to time, you need to set up new followers—perhaps to increase the number of replicas, or to replace failed nodes. How do you ensure that the new follower has an accurate copy of the leader&apos;s data?</p>
                <p className="mb-4 text-justify">Simply copying data files from one node to another is typically not sufficient: clients are constantly writing to the database, and the data is always in flux, so a standard file copy would see different parts of the database at different points in time.</p>
                
                {/* Selection Highlight & Floating Menu */}
                <div className="relative inline">
                  <span className="bg-yellow-200/50 cursor-pointer">You could make the files consistent by locking the database (making it unavailable for writes), but that would go against our goal of high availability.</span>
                  
                  {/* Floating Selection Menu */}
                  <div className="absolute -top-12 left-1/2 -translate-x-1/2 bg-surface-container-lowest border border-outline-variant rounded-md shadow-lg flex items-center p-1 gap-1 z-20 whitespace-nowrap">
                    <button className="px-2 py-1 text-xs font-medium text-on-surface hover:bg-surface-container-low rounded">Explain</button>
                    <button className="px-2 py-1 text-xs font-medium text-on-surface hover:bg-surface-container-low rounded">Summarize</button>
                    <div className="w-px h-4 bg-outline-variant mx-1"></div>
                    <button className="w-6 h-6 flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low rounded"><span className="material-symbols-outlined text-[14px]">format_ink_highlighter</span></button>
                    <button className="w-6 h-6 flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low rounded"><span className="material-symbols-outlined text-[14px]">chat_bubble</span></button>
                  </div>
                </div>
                
                <p className="mt-4 mb-4 text-justify">Fortunately, setting up a follower can usually be done without downtime. The process looks like this conceptually:</p>
                
                {/* Handwritten Annotation Simulation */}
                <div className="absolute top-95 left-20 text-blue-500/60 pointer-events-none transform -rotate-2">
                  <svg fill="none" height="20" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5" viewBox="0 0 40 20" width="40">
                    <path d="M5,15 Q20,5 35,15" />
                    <path d="M35,15 L30,10 M35,15 L30,18" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Page 163 */}
            <div className="w-125 min-h-187.5 bg-white shadow-[0_4px_20px_rgba(0,0,0,0.04)] flex flex-col relative shrink-0">
              <div className="flex-1 p-10 font-reading-body text-reading-body text-on-background">
                <div className="text-[10px] text-on-surface-variant uppercase tracking-wider mb-8 text-center font-interface-sm">163</div>
                <ol className="list-decimal pl-5 mb-4 space-y-4 text-justify">
                  <li>Take a consistent snapshot of the leader&apos;s database at some point in time—if possible, without taking a lock on the entire database. Most databases have this feature.</li>
                  <li>Copy the snapshot to the new follower node.</li>
                  <li>The follower connects to the leader and requests all data changes that have happened since the snapshot was taken. This requires that the snapshot is associated with an exact position in the leader&apos;s replication log.</li>
                  <li>When the follower has processed the backlog of data changes since the snapshot, we say it has <em>caught up</em>. It can now continue to process data changes from the leader as they happen.</li>
                </ol>
                <h4 className="font-bold text-lg mt-8 mb-2">Handling Node Outages</h4>
                <p className="text-justify">Being highly available is a primary goal for most systems. Any node in the system can go down, perhaps unexpectedly due to a fault, or perhaps for planned maintenance (such as rolling reboots for installing OS security patches).</p>
              </div>
            </div>

          </div>
          
          {/* Page Navigation Pill */}
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 bg-surface-container-lowest/90 backdrop-blur-sm border border-outline-variant rounded-full shadow-sm px-4 py-2 flex items-center gap-4">
            <button className="text-on-surface-variant hover:text-primary"><span className="material-symbols-outlined text-[18px]">navigate_before</span></button>
            <span className="text-xs font-medium tracking-wide">Page 162-163 / 613</span>
            <button className="text-on-surface-variant hover:text-primary"><span className="material-symbols-outlined text-[18px]">navigate_next</span></button>
          </div>
        </section>

        {/* Right Sidebar (AI Marginalia) */}
        <aside className="w-[320px] bg-surface-container-lowest border-l border-outline-variant flex flex-col shrink-0">
          <div className="p-4 border-b border-outline-variant flex justify-between items-center">
            <h2 className="font-interface-sm font-bold text-primary flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
              Study Assistant
            </h2>
            <button className="text-on-surface-variant hover:text-primary"><span className="material-symbols-outlined text-[18px]">more_horiz</span></button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6 bg-background">
            
            {/* User Prompt */}
            <div className="self-end max-w-[90%] bg-surface-container-low rounded-lg rounded-tr-none p-3 border border-outline-variant/30">
              <p className="text-sm">Why can&apos;t we just copy the data files to set up a new follower?</p>
            </div>
            
            {/* AI Response Notebook Style */}
            <div className="self-start w-full border-l-2 border-primary-fixed-dim pl-3 relative">
              <div className="font-reading-body text-[15px] leading-relaxed text-on-surface mb-2">
                You cannot simply copy the data files because the database is constantly in flux. Clients are continually writing new data, meaning a standard file copy would capture different parts of the database at different points in time, resulting in an inconsistent copy.
              </div>
              <div className="flex flex-wrap gap-2 mt-3">
                <button className="inline-flex items-center gap-1 bg-surface-container border border-outline-variant/50 rounded-full px-2 py-0.5 text-[11px] text-on-surface-variant hover:bg-surface-container-high transition-colors">
                  <span className="material-symbols-outlined text-[12px]">description</span>
                  Page 162
                </button>
              </div>
            </div>
            
            {/* User Prompt - Selected Text Context */}
            <div className="self-end max-w-[90%] bg-surface-container-low rounded-lg rounded-tr-none p-3 border border-outline-variant/30">
              <div className="text-[10px] text-on-surface-variant mb-1 flex items-center gap-1 uppercase tracking-wider">
                <span className="material-symbols-outlined text-[12px]">format_quote</span> Selection on Page 162
              </div>
              <p className="text-sm italic border-l-2 border-outline-variant pl-2 mb-2">&quot;You could make the files consistent by locking the database...&quot;</p>
              <p className="text-sm font-medium">Explain this tradeoff.</p>
            </div>
            
            {/* AI Response - Streaming/Typing indicator */}
            <div className="self-start w-full border-l-2 border-primary-fixed-dim pl-3 relative">
              <div className="font-reading-body text-[15px] leading-relaxed text-on-surface">
                Locking the database ensures consistency because it prevents any new writes while the copy is taking place. However, the major tradeoff is <span className="inline-flex items-center gap-1 text-primary"><span className="w-1 h-4 bg-primary animate-pulse"></span></span>
              </div>
            </div>
          </div>
          
          {/* Chat Input */}
          <div className="p-4 bg-surface-container-lowest border-t border-outline-variant">
            <div className="relative flex items-end border border-outline-variant rounded-lg bg-background focus-within:ring-2 focus-within:ring-primary focus-within:border-primary transition-all p-2">
              <textarea className="w-full bg-transparent border-none focus:ring-0 resize-none text-sm p-1 max-h-32 min-h-10 outline-none" placeholder="Ask a question about this page..."></textarea>
              <button className="p-1.5 text-primary bg-surface-container-high hover:bg-primary hover:text-on-primary rounded-md transition-colors ml-2 mb-0.5">
                <span className="material-symbols-outlined text-[18px]">send</span>
              </button>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}