import { useNavigate } from "react-router-dom";
import { Building2 } from "lucide-react";
import { riskCategoryColor, cn } from "@/lib/utils";
import type { CompanyBrief } from "@/types";

interface CompanyRowProps {
    company: CompanyBrief;
    onClick?: (company: CompanyBrief) => void;
    className?: string;
}

export default function CompanyRow({ company, onClick, className }: CompanyRowProps) {
    const navigate = useNavigate();

    const handleClick = () => {
        if (onClick) {
            onClick(company);
        } else {
            navigate(`/company/${company.cui}`);
        }
    };

    return (
        <div
            onClick={handleClick}
            className={cn(
                "group flex cursor-pointer items-center gap-4 rounded-xl border border-slate-100 bg-white/80 p-4 transition-all hover:border-nebula-200 hover:shadow-cosmic-sm",
                className
            )}
        >
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-nebula-50 text-nebula-400 transition-colors group-hover:bg-nebula-100 group-hover:text-nebula-600">
                <Building2 className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
                <p className="font-exo font-semibold text-slate-700">{company.denumire}</p>
                <p className="font-rajdhani text-sm text-slate-400">
                    CUI: {company.cui} · {company.judet}, {company.localitate} ·
                    CAEN: {company.caen_principal}
                </p>
            </div>
            <div className="flex items-center gap-3">
                <span className="font-rajdhani text-sm text-slate-400">{company.stare}</span>
                {company.risk_rating && (
                    <span
                        className={`badge-cosmic ${riskCategoryColor(company.risk_rating)}`}
                    >
                        {company.risk_rating}
                    </span>
                )}
            </div>
        </div>
    );
}
