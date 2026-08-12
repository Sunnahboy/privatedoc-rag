import React from 'react';
import Link from "next/link";

export default function LibraryPage() {
  return (
    <div className="bg-background text-on-surface font-interface-sm min-h-screen flex flex-col antialiased">
      {/* TopNavBar Component */}
      <nav className="bg-surface docked full-width top-0 border-b border-outline-variant flat no shadows flex justify-between items-center h-16 px-page-margin w-full sticky z-50">
        <div className="flex items-center gap-8">
          <span className="font-headline-md text-headline-md font-bold text-primary">PrivateDoc</span>
          <div className="hidden md:flex gap-6 h-full items-center">
            <a
              className="text-primary font-bold border-b-2 border-primary pb-1 h-full flex items-center mt-0.5 cursor-pointer active:opacity-70"
              href="#"
            >
              Library
            </a>
            <a
              className="text-on-surface-variant hover:text-primary transition-colors h-full flex items-center cursor-pointer active:opacity-70"
              href="#"
            >
              Knowledge
            </a>
          </div>
        </div>
        {/* Search Bar */}
        <div className="flex-1 max-w-md mx-8 hidden md:block">
          <div className="relative">
            <span
              className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]"
              data-icon="search"
            >
              search
            </span>
            <input
              className="w-full bg-surface-container-low border border-outline-variant rounded-full py-2 pl-10 pr-4 text-interface-sm font-interface-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              placeholder="Search documents..."
              type="text"
            />
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button className="text-on-surface-variant hover:text-primary transition-colors cursor-pointer active:opacity-70">
            <span className="material-symbols-outlined" data-icon="notifications">
              notifications
            </span>
          </button>
          <button className="text-on-surface-variant hover:text-primary transition-colors cursor-pointer active:opacity-70">
            <span className="material-symbols-outlined" data-icon="settings">
              settings
            </span>
          </button>
          <img
            alt="User avatar"
            className="w-8 h-8 rounded-full border border-outline-variant object-cover ml-2"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuBMx-ZyS2CmcnZAKb5NjYwLKSuEf00al-p0tFKZr2yEj5UqtSIFUSg9KIw0Bhq3e-uglvG9k79xlC_G-FlOVWNmomGu72l0pfBKMJOh4exsV54RW44az63jGs4Hw-xNn9Bey_2HY6wM4XwwRYuhdb2Wgs6CNYyRhG4AvtyLVWSsHIRHP399GfZIRl9GakWEyfytqsr0C5jmtDjI-JWBjpw_jKRmKjEaL86DPBTwx1jA6CIUdiUobDIO"
          />
        </div>
      </nav>

      {/* Main Layout */}
      <div className="flex-1 flex px-page-margin py-section-gap gap-section-gap max-w-360 mx-auto w-full">
        
        {/* Sidebar / Filter (Left Panel) */}
        <aside className="w-60 hidden lg:flex flex-col gap-8 shrink-0">
          {/* Categories */}
          <div className="flex flex-col gap-1">
            <button className="flex items-center gap-3 px-3 py-2 bg-surface-container rounded-lg text-primary font-bold">
              <span className="material-symbols-outlined text-[20px]" data-icon="folder" data-weight="fill">
                folder
              </span>
              All Documents
            </button>
            <button className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors">
              <span className="material-symbols-outlined text-[20px]" data-icon="schedule">
                schedule
              </span>
              Recent
            </button>
            <button className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors">
              <span className="material-symbols-outlined text-[20px]" data-icon="star">
                star
              </span>
              Starred
            </button>
            <button className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors">
              <span className="material-symbols-outlined text-[20px]" data-icon="library_books">
                library_books
              </span>
              Collections
            </button>
          </div>
          
          {/* Knowledge Stats */}
          <div className="border-t border-outline-variant pt-6">
            <h3 className="font-label-caps text-label-caps text-on-surface-variant mb-4 uppercase tracking-wider">
              Knowledge Stats
            </h3>
            <div className="flex flex-col gap-3">
              <div className="flex justify-between items-center text-on-surface">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-on-surface-variant" data-icon="stylus">
                    stylus
                  </span>
                  <span>Highlights</span>
                </div>
                <span className="font-bold">42</span>
              </div>
              <div className="flex justify-between items-center text-on-surface">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-on-surface-variant" data-icon="description">
                    description
                  </span>
                  <span>Notes</span>
                </div>
                <span className="font-bold">18</span>
              </div>
              <div className="flex justify-between items-center text-on-surface">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-on-surface-variant" data-icon="bookmark">
                    bookmark
                  </span>
                  <span>Bookmarks</span>
                </div>
                <span className="font-bold">7</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col gap-section-gap min-w-0">
          
          {/* Upload Drop Zone */}
          <div className="border border-dashed border-outline-variant rounded-xl bg-surface-container-lowest p-8 flex flex-col items-center justify-center text-center hover:bg-surface-container-low transition-colors cursor-pointer group">
            <div className="w-12 h-12 rounded-full bg-surface-container flex items-center justify-center mb-4 group-hover:bg-primary-fixed transition-colors">
              <span className="material-symbols-outlined text-primary text-[24px]" data-icon="upload_file">
                upload_file
              </span>
            </div>
            <h3 className="font-headline-md text-headline-md text-on-surface mb-2">
              Upload Document
            </h3>
            <p className="text-on-surface-variant font-interface-sm text-interface-sm mb-4">
              Drag and drop PDFs, EPUBs, or text files here
            </p>
            <button className="bg-primary text-on-primary px-6 py-2 rounded-lg font-interface-sm text-interface-sm hover:bg-primary/90 transition-colors">
              Select Files
            </button>
          </div>

          {/* Continue Reading Hero */}
          <section className="flex flex-col gap-4">
            <h2 className="font-headline-md text-headline-md text-on-surface">Continue Reading</h2>
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex gap-6 hover:shadow-[0px_10px_30px_rgba(0,0,0,0.04)] transition-shadow">
              {/* Book Cover Preview */}
              <div className="w-32 h-44 bg-surface-variant rounded-lg border border-outline-variant shrink-0 relative overflow-hidden shadow-sm">
                <img
                  alt="Document cover"
                  className="absolute inset-0 w-full h-full object-cover"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuA-AF_lN8_Uu4E_HtmgQmmDZvcQXWj3FCpjGJVHJer0CJudd5iUPa0UmXT4BOOFmT6CNpoHC4HMk8AwIN3Pkys5kYZz2uPvbwUXo7Z2q3n5X-L_B38tIozxiN5BSfoNPf1jEzClUqSFjgw9VIvqir2e8sjzr1rbb9wD_w1roRpbDCaLEwRdfWL1R6iXNdQdxiyEYECqpV-Q3m82ZfMfuGOAMEsMsatLEH3aYKFUp07rzVeXul1945wg"
                />
              </div>
              <div className="flex flex-col flex-1 justify-between py-2">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-surface-container text-on-surface-variant">
                      Technical
                    </span>
                    <span className="text-on-surface-variant text-[12px]">Last opened today</span>
                  </div>
                  <h3 className="font-display-lg text-display-lg text-on-surface leading-tight mb-2">
                    Designing Data-Intensive Applications
                  </h3>
                  <p className="text-on-surface-variant font-reading-body text-reading-body text-[16px] leading-snug line-clamp-2">
                    The big ideas behind reliable, scalable, and maintainable systems. Chapter 5: Replication.
                  </p>
                </div>
                <div className="flex items-end justify-between mt-4">
                  <div className="flex-1 max-w-sm">
                    <div className="flex justify-between text-[12px] text-on-surface-variant mb-1 font-interface-sm">
                      <span>72% completed</span>
                      <span>Page 162 of 613</span>
                    </div>
                    <div className="h-1.5 bg-surface-container rounded-full overflow-hidden">
                      <div className="h-full bg-primary w-[72%] rounded-full"></div>
                    </div>
                  </div>
                  <Link 
                    href="/workspace" 
                    className="flex items-center gap-2 bg-primary text-on-primary px-5 py-2 rounded-lg font-interface-sm text-interface-sm hover:bg-primary/90 transition-colors ml-6"
                  >
                    Continue <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                  </Link>
                </div>
              </div>
            </div>
          </section>

          {/* Document Grid */}
          <section className="flex flex-col gap-4 mt-4">
            <div className="flex justify-between items-end mb-2">
              <h2 className="font-headline-md text-headline-md text-on-surface">Recent Additions</h2>
              <div className="flex gap-2">
                <button className="p-1.5 text-primary bg-surface-container rounded hover:bg-surface-container-highest transition-colors">
                  <span className="material-symbols-outlined text-[20px]" data-icon="grid_view">
                    grid_view
                  </span>
                </button>
                <button className="p-1.5 text-on-surface-variant hover:bg-surface-container rounded transition-colors">
                  <span className="material-symbols-outlined text-[20px]" data-icon="view_list">
                    view_list
                  </span>
                </button>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              
              {/* Card 1 */}
              <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 flex flex-col gap-4 hover:shadow-[0px_4px_20px_rgba(0,0,0,0.04)] transition-all cursor-pointer group">
                <div className="flex gap-4">
                  <div className="w-20 h-28 bg-surface-variant rounded border border-outline-variant shrink-0 relative overflow-hidden shadow-sm">
                    <img
                      alt="Document cover"
                      className="absolute inset-0 w-full h-full object-cover"
                      src="https://lh3.googleusercontent.com/aida-public/AB6AXuDd6ZMs4Nk8AKfFPKEdiGs6_X6blqROFAAbq_L5VQwwuYjVT3M9AyY9GW1adsTII4STxGX8HMIwrJtAXHyIL5NNIGtN_owY4J128EsHO6QilY55D1myqmvKkMjYOU1iTIWFjAuuRU7-KiySbVwge_PykUjzVZUHH9aMKF_kMbr7aXU2yE_cF7Ig9SgX3Vze36OjOPvuT1BqgdyS3dNViK_9H2kEZh6QRIkiC4YBgXe2sQ0yj2stLkvE"
                    />
                  </div>
                  <div className="flex flex-col justify-start pt-1">
                    <h4 className="font-interface-sm text-interface-sm font-bold text-on-surface line-clamp-2 leading-snug mb-1 group-hover:text-primary transition-colors">
                      Clean Architecture: A Craftsman&apos;s Guide
                    </h4>
                    <span className="text-[12px] text-on-surface-variant mb-2">Added 2 days ago</span>
                    <div className="inline-flex items-center gap-1 text-[11px] font-bold text-on-surface-variant bg-surface-container px-2 py-0.5 rounded self-start">
                      <span className="material-symbols-outlined text-[12px]" data-icon="check_circle">
                        check_circle
                      </span>
                      Indexed
                    </div>
                  </div>
                </div>
                <div className="mt-auto">
                  <div className="flex justify-between text-[11px] text-on-surface-variant mb-1">
                    <span>12%</span>
                    <span>420 pages</span>
                  </div>
                  <div className="h-1 bg-surface-container rounded-full overflow-hidden">
                    <div className="h-full bg-primary w-[12%] rounded-full"></div>
                  </div>
                </div>
              </div>

              {/* Card 2 */}
              <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 flex flex-col gap-4 hover:shadow-[0px_4px_20px_rgba(0,0,0,0.04)] transition-all cursor-pointer group">
                <div className="flex gap-4">
                  <div className="w-20 h-28 bg-surface-variant rounded border border-outline-variant shrink-0 relative overflow-hidden shadow-sm flex items-center justify-center">
                    <span className="material-symbols-outlined text-outline text-[32px]" data-icon="description">
                      description
                    </span>
                  </div>
                  <div className="flex flex-col justify-start pt-1">
                    <h4 className="font-interface-sm text-interface-sm font-bold text-on-surface line-clamp-2 leading-snug mb-1 group-hover:text-primary transition-colors">
                      Q3 Financial Report & Analysis Draft
                    </h4>
                    <span className="text-[12px] text-on-surface-variant mb-2">Added yesterday</span>
                    <div className="inline-flex items-center gap-1 text-[11px] font-bold text-primary bg-primary-fixed px-2 py-0.5 rounded self-start animate-pulse">
                      <span className="material-symbols-outlined text-[12px]" data-icon="sync">
                        sync
                      </span>
                      Processing...
                    </div>
                  </div>
                </div>
                <div className="mt-auto">
                  <div className="flex justify-between text-[11px] text-on-surface-variant mb-1">
                    <span>0%</span>
                    <span>45 pages</span>
                  </div>
                  <div className="h-1 bg-surface-container rounded-full overflow-hidden">
                    <div className="h-full bg-surface-variant w-0 rounded-full"></div>
                  </div>
                </div>
              </div>

              {/* Card 3 */}
              <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 flex flex-col gap-4 hover:shadow-[0px_4px_20px_rgba(0,0,0,0.04)] transition-all cursor-pointer group">
                <div className="flex gap-4">
                  <div className="w-20 h-28 bg-surface-variant rounded border border-outline-variant shrink-0 relative overflow-hidden shadow-sm">
                    <img
                      alt="Document cover"
                      className="absolute inset-0 w-full h-full object-cover"
                      src="https://lh3.googleusercontent.com/aida-public/AB6AXuA5znl61_CtavoifZ-zEVr7Jjpy_iiSyYKQx_QEKDjoSV6csKY3NC73aVs4pQdNLIwf9x1SJp8CMH1a_eo2nCSJyoudjPqrOSWSPoIyBMFbI0fJtK-etzDAkfkYMOppBQV3YpuZq8FqYsY6B3zrl1Kvez1LHWeDLJx-zl5HPg5nhr8lBcx4cG_00pfC8FClEPq4pGTpqs1mBj_FwT7UTenDiMR-KkR3R1W30SEboQKjjB79kuZOMcOh"
                    />
                  </div>
                  <div className="flex flex-col justify-start pt-1">
                    <h4 className="font-interface-sm text-interface-sm font-bold text-on-surface line-clamp-2 leading-snug mb-1 group-hover:text-primary transition-colors">
                      Attention Is All You Need
                    </h4>
                    <span className="text-[12px] text-on-surface-variant mb-2">Added 1 week ago</span>
                    <div className="inline-flex items-center gap-1 text-[11px] font-bold text-on-surface-variant bg-surface-container px-2 py-0.5 rounded self-start">
                      <span className="material-symbols-outlined text-[12px]" data-icon="check_circle">
                        check_circle
                      </span>
                      Indexed
                    </div>
                  </div>
                </div>
                <div className="mt-auto">
                  <div className="flex justify-between text-[11px] text-on-surface-variant mb-1">
                    <span>100%</span>
                    <span>15 pages</span>
                  </div>
                  <div className="h-1 bg-surface-container rounded-full overflow-hidden">
                    <div className="h-full bg-secondary w-full rounded-full opacity-50"></div>
                  </div>
                </div>
              </div>

            </div>
          </section>
        </main>
      </div>
    </div>
  );
}