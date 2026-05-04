import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard", icon: "📊" },
  { to: "/data", label: "Legg til data", icon: "➕" },
  { to: "/data-overview", label: "Dataoversikt", icon: "🗂️" },
];

export default function Sidebar() {
  return (
    <aside className="w-56 flex-shrink-0 bg-sidebar text-white flex flex-col">
      <div className="px-5 py-5 border-b border-slate-700">
        <span className="text-lg font-bold tracking-tight">FundTracker</span>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              [
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-blue-600 text-white"
                  : "text-slate-300 hover:bg-sidebar-hover hover:text-white",
              ].join(" ")
            }
          >
            <span>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="px-5 py-3 border-t border-slate-700 text-xs text-slate-500">
        API: localhost:8000
      </div>
    </aside>
  );
}
