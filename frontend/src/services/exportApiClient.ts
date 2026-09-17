const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export type ExportFormat = 'csv' | 'xlsx';
export type ExportMode = 'current_page' | 'all_matching';

export interface ExportTableParams {
  format?: ExportFormat;
  export_mode?: ExportMode;
  page?: number;
  page_size?: number;
  search?: string;
  category_id?: string;
  product_id?: string;
  warehouse_id?: string;
  location_id?: string;
  supplier_id?: string;
  customer_id?: string;
  branch_id?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  as_of_date?: string;
  unit_type?: string;
}

export interface ExportReportParams {
  format?: ExportFormat;
  period_id?: string;
  date_from?: string;
  date_to?: string;
  year?: string;
  month?: string;
}

export interface ExportPlatformParams {
  format?: ExportFormat;
  search?: string;
  status?: string;
}

class ExportApiClient {
  private getToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {};
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  private extractFilename(response: Response, defaultFilename: string): string {
    const disposition = response.headers.get('Content-Disposition');
    if (disposition && disposition.includes('filename=')) {
      const matches = /filename="?([^";]+)"?/.exec(disposition);
      if (matches && matches[1]) {
        return matches[1];
      }
    }
    return defaultFilename;
  }

  private triggerDownload(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  async exportTable(businessId: string, resourceKey: string, params: ExportTableParams = {}): Promise<void> {
    const query = new URLSearchParams();
    if (params.format) query.set('format', params.format);
    if (params.export_mode) query.set('export_mode', params.export_mode);
    if (params.page) query.set('page', params.page.toString());
    if (params.page_size) query.set('page_size', params.page_size.toString());
    if (params.search) query.set('search', params.search);
    if (params.category_id) query.set('category_id', params.category_id);
    if (params.product_id) query.set('product_id', params.product_id);
    if (params.warehouse_id) query.set('warehouse_id', params.warehouse_id);
    if (params.location_id) query.set('location_id', params.location_id);
    if (params.supplier_id) query.set('supplier_id', params.supplier_id);
    if (params.customer_id) query.set('customer_id', params.customer_id);
    if (params.branch_id) query.set('branch_id', params.branch_id);
    if (params.status) query.set('status', params.status);
    if (params.date_from) query.set('date_from', params.date_from);
    if (params.date_to) query.set('date_to', params.date_to);
    if (params.as_of_date) query.set('as_of_date', params.as_of_date);
    if (params.unit_type) query.set('unit_type', params.unit_type);

    const url = `${API_BASE_URL}/businesses/${businessId}/export/table/${resourceKey}?${query.toString()}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const errorJson = await response.json().catch(() => ({}));
      const message = errorJson.message || errorJson.detail || `Export failed with status ${response.status}`;
      throw new Error(message);
    }

    const blob = await response.blob();
    const filename = this.extractFilename(response, `${resourceKey}_export.${params.format || 'csv'}`);
    this.triggerDownload(blob, filename);
  }

  async exportReport(businessId: string, resourceKey: string, params: ExportReportParams = {}): Promise<void> {
    const query = new URLSearchParams();
    if (params.format) query.set('format', params.format);
    if (params.period_id) query.set('period_id', params.period_id);
    if (params.date_from) query.set('date_from', params.date_from);
    if (params.date_to) query.set('date_to', params.date_to);
    if (params.year) query.set('year', params.year);
    if (params.month) query.set('month', params.month);

    const url = `${API_BASE_URL}/businesses/${businessId}/export/report/${resourceKey}?${query.toString()}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const errorJson = await response.json().catch(() => ({}));
      const message = errorJson.message || errorJson.detail || `Export failed with status ${response.status}`;
      throw new Error(message);
    }

    const blob = await response.blob();
    const filename = this.extractFilename(response, `${resourceKey}_report.${params.format || 'csv'}`);
    this.triggerDownload(blob, filename);
  }

  async exportPlatform(resourceKey: string, params: ExportPlatformParams = {}): Promise<void> {
    const query = new URLSearchParams();
    if (params.format) query.set('format', params.format);
    if (params.search) query.set('search', params.search);
    if (params.status) query.set('status', params.status);

    const url = `${API_BASE_URL}/platform/export/${resourceKey}?${query.toString()}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const errorJson = await response.json().catch(() => ({}));
      const message = errorJson.message || errorJson.detail || `Export failed with status ${response.status}`;
      throw new Error(message);
    }

    const blob = await response.blob();
    const filename = this.extractFilename(response, `platform_${resourceKey}.${params.format || 'csv'}`);
    this.triggerDownload(blob, filename);
  }
}

export const exportApiClient = new ExportApiClient();
