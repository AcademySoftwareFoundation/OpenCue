"use client";

import React from 'react';
import { Button } from "@/components/ui/button";
import { 
  Grid3X3, 
  List, 
  Settings, 
  Columns, 
  Play, 
  Pause, 
  Square, 
  RotateCcw, 
  Filter, 
  FilterX, 
  Download, 
  FileText, 
  FileSpreadsheet,
  Keyboard
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ToolbarProps {
  className?: string;
  onViewToggle?: (view: 'grid' | 'list') => void;
  onDensityChange?: (density: 'compact' | 'normal' | 'comfortable') => void;
  onColumnChooser?: () => void;
  onJobAction?: (action: 'pause' | 'resume' | 'kill' | 'retry') => void;
  onFilter?: (filter: string) => void;
  onClearFilters?: () => void;
  onExport?: (format: 'csv' | 'json' | 'pdf') => void;
  selectedJobs?: any[];
  currentView?: 'grid' | 'list';
  currentDensity?: 'compact' | 'normal' | 'comfortable';
  hasActiveFilters?: boolean;
}

const ToolbarButton: React.FC<{
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "default" | "secondary" | "outline";
  size?: "default" | "sm" | "lg";
  tooltip: string;
  shortcut?: string;
}> = ({ children, onClick, disabled, variant = "outline", size = "sm", tooltip, shortcut }) => (
  <TooltipProvider>
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant={variant}
          size={size}
          onClick={onClick}
          disabled={disabled}
          className="h-8 px-3"
        >
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent>
        <div className="flex flex-col items-center">
          <span>{tooltip}</span>
          {shortcut && (
            <span className="text-xs text-muted-foreground mt-1">
              <Keyboard className="inline w-3 h-3 mr-1" />
              {shortcut}
            </span>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
);

const ToolbarSeparator: React.FC = () => (
  <div className="w-px h-6 bg-border mx-2" />
);

const ToolbarGroup: React.FC<{
  title: string;
  children: React.ReactNode;
}> = ({ title, children }) => (
  <div className="flex flex-col">
    <div className="text-xs text-muted-foreground mb-1 px-1">{title}</div>
    <div className="flex items-center space-x-1">
      {children}
    </div>
  </div>
);

export const Toolbar: React.FC<ToolbarProps> = ({
  className,
  onViewToggle,
  onDensityChange,
  onColumnChooser,
  onJobAction,
  onFilter,
  onClearFilters,
  onExport,
  selectedJobs = [],
  currentView = 'list',
  currentDensity = 'normal',
  hasActiveFilters = false,
}) => {
  const hasSelectedJobs = selectedJobs.length > 0;
  const allJobsFinished = selectedJobs.every(job => job.state === 'FINISHED');

  return (
    <div className={cn(
      "flex items-end space-x-4 p-4 bg-background border-b border-border",
      "sticky top-0 z-10 shadow-sm",
      className
    )}>
      {/* View Controls Group */}
      <ToolbarGroup title="View Controls">
        <ToolbarButton
          tooltip="Switch to Grid View"
          shortcut="Ctrl+G"
          onClick={() => onViewToggle?.('grid')}
          variant={currentView === 'grid' ? 'default' : 'outline'}
        >
          <Grid3X3 className="w-4 h-4" />
        </ToolbarButton>
        
        <ToolbarButton
          tooltip="Switch to List View"
          shortcut="Ctrl+L"
          onClick={() => onViewToggle?.('list')}
          variant={currentView === 'list' ? 'default' : 'outline'}
        >
          <List className="w-4 h-4" />
        </ToolbarButton>
        
        <ToolbarButton
          tooltip="Density Settings"
          shortcut="Ctrl+D"
          onClick={() => {
            const densities: Array<'compact' | 'normal' | 'comfortable'> = ['compact', 'normal', 'comfortable'];
            const currentIndex = densities.indexOf(currentDensity);
            const nextDensity = densities[(currentIndex + 1) % densities.length];
            onDensityChange?.(nextDensity);
          }}
        >
          <Settings className="w-4 h-4" />
        </ToolbarButton>
        
        <ToolbarButton
          tooltip="Choose Columns"
          shortcut="Ctrl+K"
          onClick={onColumnChooser}
        >
          <Columns className="w-4 h-4" />
        </ToolbarButton>
      </ToolbarGroup>

      <ToolbarSeparator />

      {/* Job Actions Group */}
      <ToolbarGroup title="Job Actions">
        <ToolbarButton
          tooltip="Resume Selected Jobs"
          shortcut="Ctrl+R"
          onClick={() => onJobAction?.('resume')}
          disabled={!hasSelectedJobs || allJobsFinished}
        >
          <Play className="w-4 h-4" />
        </ToolbarButton>
        
        <ToolbarButton
          tooltip="Pause Selected Jobs"
          shortcut="Ctrl+P"
          onClick={() => onJobAction?.('pause')}
          disabled={!hasSelectedJobs || allJobsFinished}
        >
          <Pause className="w-4 h-4" />
        </ToolbarButton>
        
        <ToolbarButton
          tooltip="Kill Selected Jobs"
          shortcut="Ctrl+X"
          onClick={() => onJobAction?.('kill')}
          disabled={!hasSelectedJobs || allJobsFinished}
        >
          <Square className="w-4 h-4" />
        </ToolbarButton>
        
        <ToolbarButton
          tooltip="Retry Selected Jobs"
          shortcut="Ctrl+T"
          onClick={() => onJobAction?.('retry')}
          disabled={!hasSelectedJobs}
        >
          <RotateCcw className="w-4 h-4" />
        </ToolbarButton>
      </ToolbarGroup>

      <ToolbarSeparator />

      {/* Filters Group */}
      <ToolbarGroup title="Filters">
        <ToolbarButton
          tooltip="Quick Filter: Active Jobs"
          shortcut="Ctrl+1"
          onClick={() => onFilter?.('active')}
        >
          <Filter className="w-4 h-4" />
          <span className="ml-1 text-xs">Active</span>
        </ToolbarButton>
        
        <ToolbarButton
          tooltip="Quick Filter: Paused Jobs"
          shortcut="Ctrl+2"
          onClick={() => onFilter?.('paused')}
        >
          <Filter className="w-4 h-4" />
          <span className="ml-1 text-xs">Paused</span>
        </ToolbarButton>
        
        <ToolbarButton
          tooltip="Clear All Filters"
          shortcut="Ctrl+0"
          onClick={onClearFilters}
          disabled={!hasActiveFilters}
        >
          <FilterX className="w-4 h-4" />
        </ToolbarButton>
      </ToolbarGroup>

      <ToolbarSeparator />

      {/* Export Options Group */}
      <ToolbarGroup title="Export">
        <ToolbarButton
          tooltip="Export as CSV"
          shortcut="Ctrl+E, C"
          onClick={() => onExport?.('csv')}
        >
          <FileSpreadsheet className="w-4 h-4" />
          <span className="ml-1 text-xs">CSV</span>
        </ToolbarButton>
        
        <ToolbarButton
          tooltip="Export as JSON"
          shortcut="Ctrl+E, J"
          onClick={() => onExport?.('json')}
        >
          <FileText className="w-4 h-4" />
          <span className="ml-1 text-xs">JSON</span>
        </ToolbarButton>
        
        <ToolbarButton
          tooltip="Export as PDF"
          shortcut="Ctrl+E, P"
          onClick={() => onExport?.('pdf')}
        >
          <Download className="w-4 h-4" />
          <span className="ml-1 text-xs">PDF</span>
        </ToolbarButton>
      </ToolbarGroup>
    </div>
  );
};

export default Toolbar;