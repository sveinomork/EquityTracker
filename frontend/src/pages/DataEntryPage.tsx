import { useState } from "react";
import SectionHeader from "../components/common/SectionHeader";
import AddFundForm from "../components/forms/AddFundForm";
import AddTransactionForm from "../components/forms/AddTransactionForm";
import ManualPriceEntryForm from "../components/forms/ManualPriceEntryForm";
import AddRateForm from "../components/forms/AddRateForm";
import SyncYahooPricesButton from "../components/forms/SyncYahooPricesButton";

type Tab = "funds" | "transactions" | "prices" | "rates";

const TABS: { label: string; value: Tab; icon: string }[] = [
  { label: "Fond", value: "funds", icon: "📋" },
  { label: "Transaksjoner", value: "transactions", icon: "💱" },
  { label: "Priser", value: "prices", icon: "📈" },
  { label: "Renter", value: "rates", icon: "📊" },
];

export default function DataEntryPage() {
  const [activeTab, setActiveTab] = useState<Tab>("funds");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Legg til data</h1>
        <p className="text-sm text-gray-500 mt-1">
          Administrer fond, transaksjoner, priser og renter
        </p>
      </div>

      <div className="flex gap-2 border-b border-gray-200">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={[
              "px-4 py-3 font-medium text-sm border-b-2 transition-colors",
              activeTab === tab.value
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-800",
            ].join(" ")}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div className="max-w-lg">
        {activeTab === "funds" && (
          <div>
            <SectionHeader title="Opprett nytt fond" />
            <AddFundForm />
          </div>
        )}

        {activeTab === "transactions" && (
          <div>
            <SectionHeader title="Opprett transaksjon" />
            <AddTransactionForm />
          </div>
        )}

        {activeTab === "prices" && (
          <div className="space-y-6">
            <div>
              <SectionHeader title="Synkroniser Yahoo Finance" />
              <SyncYahooPricesButton />
            </div>
            <div className="border-t pt-6">
              <SectionHeader title="Legg til priser manuelt (HHRP)" />
              <ManualPriceEntryForm />
            </div>
          </div>
        )}

        {activeTab === "rates" && (
          <div>
            <SectionHeader title="Legg til lånerente" />
            <AddRateForm />
          </div>
        )}
      </div>
    </div>
  );
}
