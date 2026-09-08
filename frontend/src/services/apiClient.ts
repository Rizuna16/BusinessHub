import type { User, LoginPayload, RegisterPayload, TokenResponse } from '../types/auth';
import type { Account, AccountUpdatePayload } from '../types/account';
import type { Business, CreateBusinessInput, UpdateBusinessInput } from '../types/business';
import type {
  BusinessMembership,
  AddBusinessMemberInput,
  UpdateBusinessMemberInput,
} from '../types/businessMembership';
import type {
  Branch,
  BranchCreatePayload,
  BranchUpdatePayload,
} from '../types/branch';
import type { Template } from '../types/businessTemplate';
import type { BusinessConfiguration, BusinessConfigurationUpdate } from '../types/businessConfiguration';
import type { Category, CategoryCreatePayload, CategoryUpdatePayload } from '../types/category';
import type { Unit, UnitCreatePayload, UnitUpdatePayload } from '../types/unit';
import type {
  Customer,
  CustomerCreatePayload,
  CustomerUpdatePayload,
  CustomerListResponse,
} from '../types/customer';
import type {
  Product,
  ProductCreate,
  ProductUpdate,
  ProductListResponse,
  ProductVariant,
  ProductVariantCreate,
  ProductVariantUpdate,
  ProductVariantListResponse,
  Barcode,
  BarcodeCreate,
  BarcodeUpdate,
  BarcodeListResponse,
} from '../types/product';
import type {
  Supplier,
  SupplierCreatePayload,
  SupplierUpdatePayload,
  SupplierListResponse,
} from '../types/supplier';
import type {
  SupplierCatalogItem,
  SupplierCatalogItemCreatePayload,
  SupplierCatalogItemUpdatePayload,
  SupplierCatalogItemListResponse,
} from '../types/supplierCatalog';
import type {
  SalesResponse,
  SalesListResponse,
  SalesCreateInput,
  SalesUpdateInput,
  SalesLineCreateInput,
  SalesLineUpdateInput,
  SalesLineResponse,
} from '../types/sales';
import type {
  PriceList,
  PriceListCreate,
  PriceListListResponse,
  PriceEntry,
  PriceEntryCreate,
  PriceEntryListResponse,
} from '../types/pricing';
import type {
  Warehouse,
  WarehouseCreatePayload,
  WarehouseUpdatePayload,
  InventoryLocation,
  InventoryLocationCreatePayload,
  InventoryLocationUpdatePayload,
} from '../types/warehouse';
import type {
  StockBalance,
  StockMovement,
  OpeningBalancePayload,
  AdjustmentPayload,
  TransferPayload,
  TotalStockResponse,
  ValuationSummaryResponse,
} from '../types/inventory';
import type {
  StockOpname,
  StockOpnameLine,
  StockOpnameCreatePayload,
  StockOpnameLineCreatePayload,
  StockOpnameLineUpdatePayload,
} from '../types/stockOpname';
import type {
  PurchaseResponse,
  PurchaseListResponse,
  PurchaseCreateInput,
  PurchaseUpdateInput,
  PurchaseLineCreateInput,
  PurchaseLineUpdateInput,
  PurchaseLineResponse,
} from '../types/purchase';
import type {
  ReceivingResponse,
  ReceivingListResponse,
  ReceivingCreateInput,
  ReceivingUpdateInput,
  ReceivingLineCreateInput,
  ReceivingLineUpdateInput,
  ReceivingLineResponse,
} from '../types/receiving';
import type {
  PurchaseReturnResponse,
  PurchaseReturnListResponse,
  PurchaseReturnCreateInput,
  PurchaseReturnUpdateInput,
  PurchaseReturnLineCreateInput,
  PurchaseReturnLineUpdateInput,
  PurchaseReturnLineResponse,
} from '../types/purchaseReturn';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('auth_token');
  }

  public setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  public getToken(): string | null {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMessage = data.message || data.detail || (data.errors && data.errors[0]) || 'An error occurred';
      if (response.status === 401) {
        this.setToken(null);
      }
      throw new Error(errorMessage);
    }

    return data as T;
  }

  public async register(payload: RegisterPayload): Promise<User> {
    return this.request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async login(payload: LoginPayload): Promise<TokenResponse> {
    return this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async getMe(): Promise<User> {
    return this.request<User>('/auth/me', {
      method: 'GET',
    });
  }

  public async logout(): Promise<{ message: string }> {
    try {
      const res = await this.request<{ message: string }>('/auth/logout', {
        method: 'POST',
      });
      return res;
    } finally {
      this.setToken(null);
    }
  }

  public async getAccount(): Promise<Account> {
    return this.request<Account>('/account', {
      method: 'GET',
    });
  }

  public async updateAccount(payload: AccountUpdatePayload): Promise<Account> {
    return this.request<Account>('/account', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async listBusinesses(): Promise<Business[]> {
    return this.request<Business[]>('/businesses', {
      method: 'GET',
    });
  }

  public async getBusiness(id: string): Promise<Business> {
    return this.request<Business>(`/businesses/${id}`, {
      method: 'GET',
    });
  }

  public async createBusiness(payload: CreateBusinessInput): Promise<Business> {
    return this.request<Business>('/businesses', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async updateBusiness(id: string, payload: UpdateBusinessInput): Promise<Business> {
    return this.request<Business>(`/businesses/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async archiveBusiness(id: string): Promise<Business> {
    return this.request<Business>(`/businesses/${id}`, {
      method: 'DELETE',
    });
  }

  public async listBusinessMembers(businessId: string): Promise<BusinessMembership[]> {
    return this.request<BusinessMembership[]>(`/businesses/${businessId}/members`, {
      method: 'GET',
    });
  }

  public async getBusinessMember(businessId: string, membershipId: string): Promise<BusinessMembership> {
    return this.request<BusinessMembership>(`/businesses/${businessId}/members/${membershipId}`, {
      method: 'GET',
    });
  }

  public async addBusinessMember(
    businessId: string,
    payload: AddBusinessMemberInput
  ): Promise<BusinessMembership> {
    return this.request<BusinessMembership>(`/businesses/${businessId}/members`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async updateBusinessMember(
    businessId: string,
    membershipId: string,
    payload: UpdateBusinessMemberInput
  ): Promise<BusinessMembership> {
    return this.request<BusinessMembership>(`/businesses/${businessId}/members/${membershipId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async removeBusinessMember(
    businessId: string,
    membershipId: string
  ): Promise<BusinessMembership> {
    return this.request<BusinessMembership>(`/businesses/${businessId}/members/${membershipId}`, {
      method: 'DELETE',
    });
  }

  public async listBranches(businessId: string): Promise<Branch[]> {
    return this.request<Branch[]>(`/businesses/${businessId}/branches`, {
      method: 'GET',
    });
  }

  public async getBranch(businessId: string, branchId: string): Promise<Branch> {
    return this.request<Branch>(`/businesses/${businessId}/branches/${branchId}`, {
      method: 'GET',
    });
  }

  public async createBranch(
    businessId: string,
    payload: BranchCreatePayload
  ): Promise<Branch> {
    return this.request<Branch>(`/businesses/${businessId}/branches`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async updateBranch(
    businessId: string,
    branchId: string,
    payload: BranchUpdatePayload
  ): Promise<Branch> {
    return this.request<Branch>(`/businesses/${businessId}/branches/${branchId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async suspendBranch(businessId: string, branchId: string): Promise<Branch> {
    return this.request<Branch>(`/businesses/${businessId}/branches/${branchId}/suspend`, {
      method: 'POST',
    });
  }

  public async archiveBranch(businessId: string, branchId: string): Promise<Branch> {
    return this.request<Branch>(`/businesses/${businessId}/branches/${branchId}`, {
      method: 'DELETE',
    });
  }

  public async setDefaultBranch(businessId: string, branchId: string): Promise<Branch> {
    return this.request<Branch>(`/businesses/${businessId}/branches/${branchId}/default`, {
      method: 'POST',
    });
  }

  public async listTemplates(): Promise<Template[]> {
    return this.request<Template[]>('/templates', {
      method: 'GET',
    });
  }

  public async getTemplate(templateId: string): Promise<Template> {
    return this.request<Template>(`/templates/${templateId}`, {
      method: 'GET',
    });
  }

  public async getBusinessConfiguration(businessId: string): Promise<BusinessConfiguration> {
    return this.request<BusinessConfiguration>(`/businesses/${businessId}/configuration`, {
      method: 'GET',
    });
  }

  public async updateBusinessConfiguration(
    businessId: string,
    payload: BusinessConfigurationUpdate
  ): Promise<BusinessConfiguration> {
    return this.request<BusinessConfiguration>(`/businesses/${businessId}/configuration`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async listCategories(
    businessId: string,
    parentId?: string | null,
    includeArchived: boolean = false
  ): Promise<Category[]> {
    const params = new URLSearchParams();
    if (parentId) params.set('parent_id', parentId);
    if (includeArchived) params.set('include_archived', 'true');
    const qs = params.toString();
    return this.request<Category[]>(`/businesses/${businessId}/categories${qs ? `?${qs}` : ''}`, {
      method: 'GET',
    });
  }

  public async getCategory(businessId: string, categoryId: string): Promise<Category> {
    return this.request<Category>(`/businesses/${businessId}/categories/${categoryId}`, {
      method: 'GET',
    });
  }

  public async createCategory(businessId: string, payload: CategoryCreatePayload): Promise<Category> {
    return this.request<Category>(`/businesses/${businessId}/categories`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async updateCategory(businessId: string, categoryId: string, payload: CategoryUpdatePayload): Promise<Category> {
    return this.request<Category>(`/businesses/${businessId}/categories/${categoryId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async archiveCategory(businessId: string, categoryId: string): Promise<Category> {
    return this.request<Category>(`/businesses/${businessId}/categories/${categoryId}`, {
      method: 'DELETE',
    });
  }

  public async listUnits(
    businessId: string,
    unitType?: string | null,
    includeArchived: boolean = false
  ): Promise<Unit[]> {
    const params = new URLSearchParams();
    if (unitType) params.set('unit_type', unitType);
    if (includeArchived) params.set('include_archived', 'true');
    const qs = params.toString();
    return this.request<Unit[]>(`/businesses/${businessId}/units${qs ? `?${qs}` : ''}`, {
      method: 'GET',
    });
  }

  public async getUnit(businessId: string, unitId: string): Promise<Unit> {
    return this.request<Unit>(`/businesses/${businessId}/units/${unitId}`, {
      method: 'GET',
    });
  }

  public async createUnit(businessId: string, payload: UnitCreatePayload): Promise<Unit> {
    return this.request<Unit>(`/businesses/${businessId}/units`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async updateUnit(businessId: string, unitId: string, payload: UnitUpdatePayload): Promise<Unit> {
    return this.request<Unit>(`/businesses/${businessId}/units/${unitId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async archiveUnit(businessId: string, unitId: string): Promise<Unit> {
    return this.request<Unit>(`/businesses/${businessId}/units/${unitId}`, {
      method: 'DELETE',
    });
  }

  // ============================================================
  // Customer
  // ============================================================
  public async listCustomers(
    businessId: string,
    params?: {
      search?: string;
      status?: string;
      customer_type?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<CustomerListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.search) searchParams.set('search', params.search);
      if (params.status) searchParams.set('status', params.status);
      if (params.customer_type) searchParams.set('customer_type', params.customer_type);
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
    }
    const qs = searchParams.toString();
    return this.request<CustomerListResponse>(
      `/businesses/${businessId}/customers${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getCustomer(businessId: string, customerId: string): Promise<Customer> {
    return this.request<Customer>(`/businesses/${businessId}/customers/${customerId}`, {
      method: 'GET',
    });
  }

  public async createCustomer(businessId: string, payload: CustomerCreatePayload): Promise<Customer> {
    return this.request<Customer>(`/businesses/${businessId}/customers`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async updateCustomer(
    businessId: string,
    customerId: string,
    payload: CustomerUpdatePayload
  ): Promise<Customer> {
    return this.request<Customer>(`/businesses/${businessId}/customers/${customerId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async archiveCustomer(businessId: string, customerId: string): Promise<Customer> {
    return this.request<Customer>(`/businesses/${businessId}/customers/${customerId}`, {
      method: 'DELETE',
    });
  }

  public async activateCustomer(businessId: string, customerId: string): Promise<Customer> {
    return this.request<Customer>(`/businesses/${businessId}/customers/${customerId}/activate`, {
      method: 'POST',
    });
  }

  public async deactivateCustomer(businessId: string, customerId: string): Promise<Customer> {
    return this.request<Customer>(`/businesses/${businessId}/customers/${customerId}/deactivate`, {
      method: 'POST',
    });
  }

  public async listProducts(
    businessId: string,
    params?: {
      status?: string;
      product_type?: string;
      category_id?: string;
      search?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<ProductListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.status) searchParams.set('status', params.status);
      if (params.product_type) searchParams.set('product_type', params.product_type);
      if (params.category_id) searchParams.set('category_id', params.category_id);
      if (params.search) searchParams.set('search', params.search);
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
    }
    const qs = searchParams.toString();
    return this.request<ProductListResponse>(`/businesses/${businessId}/products${qs ? `?${qs}` : ''}`, {
      method: 'GET',
    });
  }

  public async getProduct(businessId: string, productId: string): Promise<Product> {
    return this.request<Product>(`/businesses/${businessId}/products/${productId}`, {
      method: 'GET',
    });
  }

  public async createProduct(
    businessId: string,
    payload: ProductCreate
  ): Promise<Product> {
    return this.request<Product>(`/businesses/${businessId}/products`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async updateProduct(
    businessId: string,
    productId: string,
    payload: ProductUpdate
  ): Promise<Product> {
    return this.request<Product>(`/businesses/${businessId}/products/${productId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async archiveProduct(
    businessId: string,
    productId: string
  ): Promise<Product> {
    return this.request<Product>(`/businesses/${businessId}/products/${productId}`, {
      method: 'DELETE',
    });
  }

  // ============================================================
  // Product Variant
  // ============================================================
  public async listProductVariants(
    businessId: string,
    productId: string
  ): Promise<ProductVariantListResponse> {
    return this.request<ProductVariantListResponse>(
      `/businesses/${businessId}/products/${productId}/variants`,
      { method: 'GET' }
    );
  }

  public async getProductVariant(
    businessId: string,
    productId: string,
    variantId: string
  ): Promise<ProductVariant> {
    return this.request<ProductVariant>(
      `/businesses/${businessId}/products/${productId}/variants/${variantId}`,
      { method: 'GET' }
    );
  }

  public async createProductVariant(
    businessId: string,
    productId: string,
    payload: ProductVariantCreate
  ): Promise<ProductVariant> {
    return this.request<ProductVariant>(
      `/businesses/${businessId}/products/${productId}/variants`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  }

  public async updateProductVariant(
    businessId: string,
    productId: string,
    variantId: string,
    payload: ProductVariantUpdate
  ): Promise<ProductVariant> {
    return this.request<ProductVariant>(
      `/businesses/${businessId}/products/${productId}/variants/${variantId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }
    );
  }

  public async archiveProductVariant(
    businessId: string,
    productId: string,
    variantId: string
  ): Promise<ProductVariant> {
    return this.request<ProductVariant>(
      `/businesses/${businessId}/products/${productId}/variants/${variantId}`,
      { method: 'DELETE' }
    );
  }

  // ============================================================
  // Barcode
  // ============================================================
  public async listBarcodes(
    businessId: string,
    params?: { product_id?: string; variant_id?: string; status?: string }
  ): Promise<BarcodeListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.product_id) searchParams.set('product_id', params.product_id);
      if (params.variant_id) searchParams.set('variant_id', params.variant_id);
      if (params.status) searchParams.set('status', params.status);
    }
    const qs = searchParams.toString();
    return this.request<BarcodeListResponse>(
      `/businesses/${businessId}/barcodes${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getBarcode(
    businessId: string,
    barcodeId: string
  ): Promise<Barcode> {
    return this.request<Barcode>(`/businesses/${businessId}/barcodes/${barcodeId}`, {
      method: 'GET',
    });
  }

  public async createBarcode(
    businessId: string,
    payload: BarcodeCreate
  ): Promise<Barcode> {
    return this.request<Barcode>(`/businesses/${businessId}/barcodes`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async updateBarcode(
    businessId: string,
    barcodeId: string,
    payload: BarcodeUpdate
  ): Promise<Barcode> {
    return this.request<Barcode>(`/businesses/${businessId}/barcodes/${barcodeId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async archiveBarcode(
    businessId: string,
    barcodeId: string
  ): Promise<Barcode> {
    return this.request<Barcode>(`/businesses/${businessId}/barcodes/${barcodeId}`, {
      method: 'DELETE',
    });
  }

  // ============================================================
  // Pricing & Price List
  // ============================================================
  public async listPriceLists(businessId: string): Promise<PriceListListResponse> {
    return this.request<PriceListListResponse>(`/businesses/${businessId}/price-lists`, {
      method: 'GET',
    });
  }

  public async getPriceList(businessId: string, priceListId: string): Promise<PriceList> {
    return this.request<PriceList>(`/businesses/${businessId}/price-lists/${priceListId}`, {
      method: 'GET',
    });
  }

  public async createPriceList(businessId: string, payload: PriceListCreate): Promise<PriceList> {
    return this.request<PriceList>(`/businesses/${businessId}/price-lists`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async archivePriceList(businessId: string, priceListId: string): Promise<PriceList> {
    return this.request<PriceList>(`/businesses/${businessId}/price-lists/${priceListId}`, {
      method: 'DELETE',
    });
  }

  public async listPriceEntries(businessId: string, priceListId: string): Promise<PriceEntryListResponse> {
    return this.request<PriceEntryListResponse>(
      `/businesses/${businessId}/price-lists/${priceListId}/prices`,
      { method: 'GET' }
    );
  }

  public async createPriceEntry(
    businessId: string,
    priceListId: string,
    payload: PriceEntryCreate
  ): Promise<PriceEntry> {
    return this.request<PriceEntry>(
      `/businesses/${businessId}/price-lists/${priceListId}/prices`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  }

  public async archivePriceEntry(
    businessId: string,
    priceListId: string,
    priceId: string
  ): Promise<PriceEntry> {
    return this.request<PriceEntry>(
      `/businesses/${businessId}/price-lists/${priceListId}/prices/${priceId}`,
      { method: 'DELETE' }
    );
  }

  // ============================================================
  // Warehouse & Inventory Location
  // ============================================================
  public async listWarehouses(businessId: string): Promise<Warehouse[]> {
    return this.request<Warehouse[]>(`/businesses/${businessId}/warehouses`, { method: 'GET' });
  }

  public async getWarehouse(businessId: string, warehouseId: string): Promise<Warehouse> {
    return this.request<Warehouse>(`/businesses/${businessId}/warehouses/${warehouseId}`, { method: 'GET' });
  }

  public async createWarehouse(businessId: string, payload: WarehouseCreatePayload): Promise<Warehouse> {
    return this.request<Warehouse>(`/businesses/${businessId}/warehouses`, { method: 'POST', body: JSON.stringify(payload) });
  }

  public async updateWarehouse(businessId: string, warehouseId: string, payload: WarehouseUpdatePayload): Promise<Warehouse> {
    return this.request<Warehouse>(`/businesses/${businessId}/warehouses/${warehouseId}`, { method: 'PATCH', body: JSON.stringify(payload) });
  }

  public async suspendWarehouse(businessId: string, warehouseId: string): Promise<Warehouse> {
    return this.request<Warehouse>(`/businesses/${businessId}/warehouses/${warehouseId}/suspend`, { method: 'POST' });
  }

  public async activateWarehouse(businessId: string, warehouseId: string): Promise<Warehouse> {
    return this.request<Warehouse>(`/businesses/${businessId}/warehouses/${warehouseId}/activate`, { method: 'POST' });
  }

  public async archiveWarehouse(businessId: string, warehouseId: string): Promise<Warehouse> {
    return this.request<Warehouse>(`/businesses/${businessId}/warehouses/${warehouseId}`, { method: 'DELETE' });
  }

  public async listWareLocations(businessId: string, warehouseId: string): Promise<InventoryLocation[]> {
    return this.request<InventoryLocation[]>(`/businesses/${businessId}/warehouses/${warehouseId}/locations`, { method: 'GET' });
  }

  public async getLocation(businessId: string, warehouseId: string, locationId: string): Promise<InventoryLocation> {
    return this.request<InventoryLocation>(`/businesses/${businessId}/warehouses/${warehouseId}/locations/${locationId}`, { method: 'GET' });
  }

  public async createLocation(businessId: string, warehouseId: string, payload: InventoryLocationCreatePayload): Promise<InventoryLocation> {
    return this.request<InventoryLocation>(`/businesses/${businessId}/warehouses/${warehouseId}/locations`, { method: 'POST', body: JSON.stringify(payload) });
  }

  public async updateLocation(businessId: string, warehouseId: string, locationId: string, payload: InventoryLocationUpdatePayload): Promise<InventoryLocation> {
    return this.request<InventoryLocation>(`/businesses/${businessId}/warehouses/${warehouseId}/locations/${locationId}`, { method: 'PATCH', body: JSON.stringify(payload) });
  }

  public async archiveLocation(businessId: string, warehouseId: string, locationId: string): Promise<InventoryLocation> {
    return this.request<InventoryLocation>(`/businesses/${businessId}/warehouses/${warehouseId}/locations/${locationId}`, { method: 'DELETE' });
  }

  // ============================================================
  // Inventory
  // ============================================================
  public async listStockBalances(
    businessId: string,
    params?: { inventory_location_id?: string; product_id?: string; variant_id?: string }
  ): Promise<StockBalance[]> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.inventory_location_id) searchParams.set('inventory_location_id', params.inventory_location_id);
      if (params.product_id) searchParams.set('product_id', params.product_id);
      if (params.variant_id) searchParams.set('variant_id', params.variant_id);
    }
    const qs = searchParams.toString();
    return this.request<StockBalance[]>(`/businesses/${businessId}/inventory/stock${qs ? `?${qs}` : ''}`, { method: 'GET' });
  }

  public async getStockBalance(businessId: string, stockId: string): Promise<StockBalance> {
    return this.request<StockBalance>(`/businesses/${businessId}/inventory/stock/${stockId}`, { method: 'GET' });
  }

  public async getTotalStock(businessId: string, productId: string, variantId?: string | null): Promise<TotalStockResponse> {
    const params = new URLSearchParams({ product_id: productId });
    if (variantId) params.set('variant_id', variantId);
    return this.request<TotalStockResponse>(`/businesses/${businessId}/inventory/stock/total?${params.toString()}`, { method: 'GET' });
  }

  public async createOpeningBalance(businessId: string, payload: OpeningBalancePayload): Promise<StockMovement> {
    return this.request<StockMovement>(`/businesses/${businessId}/inventory/opening-balance`, { method: 'POST', body: JSON.stringify(payload) });
  }

  public async adjustIn(businessId: string, payload: AdjustmentPayload): Promise<StockMovement> {
    return this.request<StockMovement>(`/businesses/${businessId}/inventory/adjustments/in`, { method: 'POST', body: JSON.stringify(payload) });
  }

  public async adjustOut(businessId: string, payload: AdjustmentPayload): Promise<StockMovement> {
    return this.request<StockMovement>(`/businesses/${businessId}/inventory/adjustments/out`, { method: 'POST', body: JSON.stringify(payload) });
  }

  public async createTransfer(businessId: string, payload: TransferPayload): Promise<StockMovement[]> {
    return this.request<StockMovement[]>(`/businesses/${businessId}/inventory/transfers`, { method: 'POST', body: JSON.stringify(payload) });
  }

  public async getValuationSummary(businessId: string): Promise<ValuationSummaryResponse> {
    return this.request<ValuationSummaryResponse>(`/businesses/${businessId}/inventory/valuation`, { method: 'GET' });
  }

  public async listMovements(
    businessId: string,
    params?: { movement_type?: string; inventory_location_id?: string; product_id?: string; variant_id?: string }
  ): Promise<StockMovement[]> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.movement_type) searchParams.set('movement_type', params.movement_type);
      if (params.inventory_location_id) searchParams.set('inventory_location_id', params.inventory_location_id);
      if (params.product_id) searchParams.set('product_id', params.product_id);
      if (params.variant_id) searchParams.set('variant_id', params.variant_id);
    }
    const qs = searchParams.toString();
    return this.request<StockMovement[]>(`/businesses/${businessId}/inventory/movements${qs ? `?${qs}` : ''}`, { method: 'GET' });
  }

  // ============================================================
  // Stock Opname
  // ============================================================
  public async listStockOpnames(
    businessId: string,
    params?: { status?: string; inventory_location_id?: string }
  ): Promise<StockOpname[]> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.status) searchParams.set('status', params.status);
      if (params.inventory_location_id) searchParams.set('inventory_location_id', params.inventory_location_id);
    }
    const qs = searchParams.toString();
    return this.request<StockOpname[]>(`/businesses/${businessId}/inventory/stock-opnames${qs ? `?${qs}` : ''}`, { method: 'GET' });
  }

  public async getStockOpname(businessId: string, opnameId: string): Promise<StockOpname> {
    return this.request<StockOpname>(`/businesses/${businessId}/inventory/stock-opnames/${opnameId}`, { method: 'GET' });
  }

  public async createStockOpname(businessId: string, payload: StockOpnameCreatePayload): Promise<StockOpname> {
    return this.request<StockOpname>(`/businesses/${businessId}/inventory/stock-opnames`, { method: 'POST', body: JSON.stringify(payload) });
  }

  public async deleteStockOpname(businessId: string, opnameId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/businesses/${businessId}/inventory/stock-opnames/${opnameId}`, { method: 'DELETE' });
  }

  public async addStockOpnameLine(businessId: string, opnameId: string, payload: StockOpnameLineCreatePayload): Promise<StockOpnameLine> {
    return this.request<StockOpnameLine>(`/businesses/${businessId}/inventory/stock-opnames/${opnameId}/lines`, { method: 'POST', body: JSON.stringify(payload) });
  }

  public async updateStockOpnameLineCount(
    businessId: string,
    opnameId: string,
    lineId: string,
    payload: StockOpnameLineUpdatePayload
  ): Promise<StockOpnameLine> {
    return this.request<StockOpnameLine>(`/businesses/${businessId}/inventory/stock-opnames/${opnameId}/lines/${lineId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async deleteStockOpnameLine(businessId: string, opnameId: string, lineId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/businesses/${businessId}/inventory/stock-opnames/${opnameId}/lines/${lineId}`, { method: 'DELETE' });
  }

  public async finalizeStockOpname(businessId: string, opnameId: string): Promise<StockOpname> {
    return this.request<StockOpname>(`/businesses/${businessId}/inventory/stock-opnames/${opnameId}/finalize`, { method: 'POST' });
  }

  // ============================================================
  // Supplier
  // ============================================================
  public async listSuppliers(
    businessId: string,
    params?: {
      search?: string;
      status?: string;
      supplier_type?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<SupplierListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.search) searchParams.set('search', params.search);
      if (params.status) searchParams.set('status', params.status);
      if (params.supplier_type) searchParams.set('supplier_type', params.supplier_type);
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
    }
    const qs = searchParams.toString();
    return this.request<SupplierListResponse>(
      `/businesses/${businessId}/suppliers${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getSupplier(businessId: string, supplierId: string): Promise<Supplier> {
    return this.request<Supplier>(`/businesses/${businessId}/suppliers/${supplierId}`, {
      method: 'GET',
    });
  }

  public async createSupplier(businessId: string, payload: SupplierCreatePayload): Promise<Supplier> {
    return this.request<Supplier>(`/businesses/${businessId}/suppliers`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async updateSupplier(
    businessId: string,
    supplierId: string,
    payload: SupplierUpdatePayload
  ): Promise<Supplier> {
    return this.request<Supplier>(`/businesses/${businessId}/suppliers/${supplierId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async archiveSupplier(businessId: string, supplierId: string): Promise<Supplier> {
    return this.request<Supplier>(`/businesses/${businessId}/suppliers/${supplierId}`, {
      method: 'DELETE',
    });
  }

  public async activateSupplier(businessId: string, supplierId: string): Promise<Supplier> {
    return this.request<Supplier>(`/businesses/${businessId}/suppliers/${supplierId}/activate`, {
      method: 'POST',
    });
  }

  public async deactivateSupplier(businessId: string, supplierId: string): Promise<Supplier> {
    return this.request<Supplier>(`/businesses/${businessId}/suppliers/${supplierId}/deactivate`, {
      method: 'POST',
    });
  }

  // ============================================================
  // Purchase
  // ============================================================
  public async listPurchases(
    businessId: string,
    params?: {
      search?: string;
      status?: string;
      supplier_id?: string;
      branch_id?: string;
      receiving_status?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<PurchaseListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.search) searchParams.set('search', params.search);
      if (params.status) searchParams.set('status', params.status);
      if (params.supplier_id) searchParams.set('supplier_id', params.supplier_id);
      if (params.branch_id) searchParams.set('branch_id', params.branch_id);
      if (params.receiving_status) searchParams.set('receiving_status', params.receiving_status);
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
    }
    const qs = searchParams.toString();
    return this.request<PurchaseListResponse>(
      `/businesses/${businessId}/purchases${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getPurchase(businessId: string, purchaseId: string): Promise<PurchaseResponse> {
    return this.request<PurchaseResponse>(
      `/businesses/${businessId}/purchases/${purchaseId}`,
      { method: 'GET' }
    );
  }

  public async createPurchase(businessId: string, payload: PurchaseCreateInput): Promise<PurchaseResponse> {
    return this.request<PurchaseResponse>(
      `/businesses/${businessId}/purchases`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async updatePurchase(businessId: string, purchaseId: string, payload: PurchaseUpdateInput): Promise<PurchaseResponse> {
    return this.request<PurchaseResponse>(
      `/businesses/${businessId}/purchases/${purchaseId}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    );
  }

  public async deletePurchase(businessId: string, purchaseId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/businesses/${businessId}/purchases/${purchaseId}`,
      { method: 'DELETE' }
    );
  }

  public async addPurchaseLine(businessId: string, purchaseId: string, payload: PurchaseLineCreateInput): Promise<PurchaseLineResponse> {
    return this.request<PurchaseLineResponse>(
      `/businesses/${businessId}/purchases/${purchaseId}/lines`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async updatePurchaseLine(
    businessId: string,
    purchaseId: string,
    lineId: string,
    payload: PurchaseLineUpdateInput
  ): Promise<PurchaseLineResponse> {
    return this.request<PurchaseLineResponse>(
      `/businesses/${businessId}/purchases/${purchaseId}/lines/${lineId}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    );
  }

  public async deletePurchaseLine(businessId: string, purchaseId: string, lineId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/businesses/${businessId}/purchases/${purchaseId}/lines/${lineId}`,
      { method: 'DELETE' }
    );
  }

  public async finalizePurchase(businessId: string, purchaseId: string): Promise<PurchaseResponse> {
    return this.request<PurchaseResponse>(
      `/businesses/${businessId}/purchases/${purchaseId}/finalize`,
      { method: 'POST' }
    );
  }

  public async cancelPurchase(businessId: string, purchaseId: string): Promise<PurchaseResponse> {
    return this.request<PurchaseResponse>(
      `/businesses/${businessId}/purchases/${purchaseId}/cancel`,
      { method: 'POST' }
    );
  }

  // ============================================================
  // Receiving
  // ============================================================
  public async listReceivings(
    businessId: string,
    params?: {
      search?: string;
      status?: string;
      purchase_id?: string;
      inventory_location_id?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<ReceivingListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.search) searchParams.set('search', params.search);
      if (params.status) searchParams.set('status', params.status);
      if (params.purchase_id) searchParams.set('purchase_id', params.purchase_id);
      if (params.inventory_location_id) searchParams.set('inventory_location_id', params.inventory_location_id);
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
    }
    const qs = searchParams.toString();
    return this.request<ReceivingListResponse>(
      `/businesses/${businessId}/receivings${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getReceiving(businessId: string, receivingId: string): Promise<ReceivingResponse> {
    return this.request<ReceivingResponse>(
      `/businesses/${businessId}/receivings/${receivingId}`,
      { method: 'GET' }
    );
  }

  public async createReceiving(businessId: string, payload: ReceivingCreateInput): Promise<ReceivingResponse> {
    return this.request<ReceivingResponse>(
      `/businesses/${businessId}/receivings`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async updateReceiving(businessId: string, receivingId: string, payload: ReceivingUpdateInput): Promise<ReceivingResponse> {
    return this.request<ReceivingResponse>(
      `/businesses/${businessId}/receivings/${receivingId}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    );
  }

  public async deleteReceiving(businessId: string, receivingId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/businesses/${businessId}/receivings/${receivingId}`,
      { method: 'DELETE' }
    );
  }

  public async addReceivingLine(businessId: string, receivingId: string, payload: ReceivingLineCreateInput): Promise<ReceivingLineResponse> {
    return this.request<ReceivingLineResponse>(
      `/businesses/${businessId}/receivings/${receivingId}/lines`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async updateReceivingLine(
    businessId: string,
    receivingId: string,
    lineId: string,
    payload: ReceivingLineUpdateInput
  ): Promise<ReceivingLineResponse> {
    return this.request<ReceivingLineResponse>(
      `/businesses/${businessId}/receivings/${receivingId}/lines/${lineId}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    );
  }

  public async deleteReceivingLine(businessId: string, receivingId: string, lineId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/businesses/${businessId}/receivings/${receivingId}/lines/${lineId}`,
      { method: 'DELETE' }
    );
  }

  public async finalizeReceiving(businessId: string, receivingId: string): Promise<ReceivingResponse> {
    return this.request<ReceivingResponse>(
      `/businesses/${businessId}/receivings/${receivingId}/finalize`,
      { method: 'POST' }
    );
  }

  public async cancelReceiving(businessId: string, receivingId: string): Promise<ReceivingResponse> {
    return this.request<ReceivingResponse>(
      `/businesses/${businessId}/receivings/${receivingId}/cancel`,
      { method: 'POST' }
    );
  }

  // ============================================================
  // Purchase Return
  // ============================================================
  public async listPurchaseReturns(
    businessId: string,
    params?: {
      search?: string;
      status?: string;
      purchase_id?: string;
      inventory_location_id?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<PurchaseReturnListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.search) searchParams.set('search', params.search);
      if (params.status) searchParams.set('status', params.status);
      if (params.purchase_id) searchParams.set('purchase_id', params.purchase_id);
      if (params.inventory_location_id) searchParams.set('inventory_location_id', params.inventory_location_id);
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
    }
    const qs = searchParams.toString();
    return this.request<PurchaseReturnListResponse>(
      `/businesses/${businessId}/purchase-returns${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getPurchaseReturn(businessId: string, returnId: string): Promise<PurchaseReturnResponse> {
    return this.request<PurchaseReturnResponse>(
      `/businesses/${businessId}/purchase-returns/${returnId}`,
      { method: 'GET' }
    );
  }

  public async createPurchaseReturn(businessId: string, payload: PurchaseReturnCreateInput): Promise<PurchaseReturnResponse> {
    return this.request<PurchaseReturnResponse>(
      `/businesses/${businessId}/purchase-returns`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async updatePurchaseReturn(businessId: string, returnId: string, payload: PurchaseReturnUpdateInput): Promise<PurchaseReturnResponse> {
    return this.request<PurchaseReturnResponse>(
      `/businesses/${businessId}/purchase-returns/${returnId}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    );
  }

  public async deletePurchaseReturn(businessId: string, returnId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/businesses/${businessId}/purchase-returns/${returnId}`,
      { method: 'DELETE' }
    );
  }

  public async addPurchaseReturnLine(businessId: string, returnId: string, payload: PurchaseReturnLineCreateInput): Promise<PurchaseReturnLineResponse> {
    return this.request<PurchaseReturnLineResponse>(
      `/businesses/${businessId}/purchase-returns/${returnId}/lines`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async updatePurchaseReturnLine(
    businessId: string,
    returnId: string,
    lineId: string,
    payload: PurchaseReturnLineUpdateInput
  ): Promise<PurchaseReturnLineResponse> {
    return this.request<PurchaseReturnLineResponse>(
      `/businesses/${businessId}/purchase-returns/${returnId}/lines/${lineId}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    );
  }

  public async deletePurchaseReturnLine(businessId: string, returnId: string, lineId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/businesses/${businessId}/purchase-returns/${returnId}/lines/${lineId}`,
      { method: 'DELETE' }
    );
  }

  public async finalizePurchaseReturn(businessId: string, returnId: string): Promise<PurchaseReturnResponse> {
    return this.request<PurchaseReturnResponse>(
      `/businesses/${businessId}/purchase-returns/${returnId}/finalize`,
      { method: 'POST' }
    );
  }

  public async cancelPurchaseReturn(businessId: string, returnId: string): Promise<PurchaseReturnResponse> {
    return this.request<PurchaseReturnResponse>(
      `/businesses/${businessId}/purchase-returns/${returnId}/cancel`,
      { method: 'POST' }
    );
  }

  // ============================================================
  // Supplier Catalog
  // ============================================================
  public async listSupplierCatalogItems(
    businessId: string,
    params?: {
      search?: string;
      supplier_id?: string;
      product_id?: string;
      variant_id?: string;
      status?: string;
      is_preferred?: boolean;
      page?: number;
      page_size?: number;
    }
  ): Promise<SupplierCatalogItemListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.search) searchParams.set('search', params.search);
      if (params.supplier_id) searchParams.set('supplier_id', params.supplier_id);
      if (params.product_id) searchParams.set('product_id', params.product_id);
      if (params.variant_id) searchParams.set('variant_id', params.variant_id);
      if (params.status) searchParams.set('status', params.status);
      if (params.is_preferred !== undefined) searchParams.set('is_preferred', String(params.is_preferred));
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
    }
    const qs = searchParams.toString();
    return this.request<SupplierCatalogItemListResponse>(
      `/businesses/${businessId}/supplier-catalog${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getSupplierCatalogItem(businessId: string, catalogId: string): Promise<SupplierCatalogItem> {
    return this.request<SupplierCatalogItem>(
      `/businesses/${businessId}/supplier-catalog/${catalogId}`,
      { method: 'GET' }
    );
  }

  public async createSupplierCatalogItem(
    businessId: string,
    payload: SupplierCatalogItemCreatePayload
  ): Promise<SupplierCatalogItem> {
    return this.request<SupplierCatalogItem>(
      `/businesses/${businessId}/supplier-catalog`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async updateSupplierCatalogItem(
    businessId: string,
    catalogId: string,
    payload: SupplierCatalogItemUpdatePayload
  ): Promise<SupplierCatalogItem> {
    return this.request<SupplierCatalogItem>(
      `/businesses/${businessId}/supplier-catalog/${catalogId}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    );
  }

  public async archiveSupplierCatalogItem(businessId: string, catalogId: string): Promise<SupplierCatalogItem> {
    return this.request<SupplierCatalogItem>(
      `/businesses/${businessId}/supplier-catalog/${catalogId}`,
      { method: 'DELETE' }
    );
  }

  public async activateSupplierCatalogItem(businessId: string, catalogId: string): Promise<SupplierCatalogItem> {
    return this.request<SupplierCatalogItem>(
      `/businesses/${businessId}/supplier-catalog/${catalogId}/activate`,
      { method: 'POST' }
    );
  }

  public async deactivateSupplierCatalogItem(businessId: string, catalogId: string): Promise<SupplierCatalogItem> {
    return this.request<SupplierCatalogItem>(
      `/businesses/${businessId}/supplier-catalog/${catalogId}/deactivate`,
      { method: 'POST' }
    );
  }

  // ============================================================
  // Sales
  // ============================================================
  public async listSales(
    businessId: string,
    params?: {
      search?: string;
      status?: string;
      customer_id?: string;
      branch_id?: string;
      date_from?: string;
      date_to?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<SalesListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.search) searchParams.set('search', params.search);
      if (params.status) searchParams.set('status', params.status);
      if (params.customer_id) searchParams.set('customer_id', params.customer_id);
      if (params.branch_id) searchParams.set('branch_id', params.branch_id);
      if (params.date_from) searchParams.set('date_from', params.date_from);
      if (params.date_to) searchParams.set('date_to', params.date_to);
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
    }
    const qs = searchParams.toString();
    return this.request<SalesListResponse>(
      `/businesses/${businessId}/sales${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getSales(businessId: string, salesId: string): Promise<SalesResponse> {
    return this.request<SalesResponse>(`/businesses/${businessId}/sales/${salesId}`, {
      method: 'GET',
    });
  }

  public async createSales(businessId: string, payload: SalesCreateInput): Promise<SalesResponse> {
    return this.request<SalesResponse>(`/businesses/${businessId}/sales`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async updateSales(
    businessId: string,
    salesId: string,
    payload: SalesUpdateInput
  ): Promise<SalesResponse> {
    return this.request<SalesResponse>(`/businesses/${businessId}/sales/${salesId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async deleteSalesDraft(businessId: string, salesId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/businesses/${businessId}/sales/${salesId}`, {
      method: 'DELETE',
    });
  }

  public async addSalesLine(
    businessId: string,
    salesId: string,
    payload: SalesLineCreateInput
  ): Promise<SalesLineResponse> {
    return this.request<SalesLineResponse>(`/businesses/${businessId}/sales/${salesId}/lines`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async updateSalesLine(
    businessId: string,
    salesId: string,
    lineId: string,
    payload: SalesLineUpdateInput
  ): Promise<SalesLineResponse> {
    return this.request<SalesLineResponse>(
      `/businesses/${businessId}/sales/${salesId}/lines/${lineId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }
    );
  }

  public async deleteSalesLine(
    businessId: string,
    salesId: string,
    lineId: string
  ): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/businesses/${businessId}/sales/${salesId}/lines/${lineId}`,
      { method: 'DELETE' }
    );
  }

  public async finalizeSales(businessId: string, salesId: string, params?: { inventory_location_id?: string }): Promise<SalesResponse> {
    const searchParams = new URLSearchParams();
    if (params?.inventory_location_id) {
      searchParams.set('inventory_location_id', params.inventory_location_id);
    }
    const qs = searchParams.toString();
    return this.request<SalesResponse>(`/businesses/${businessId}/sales/${salesId}/finalize${qs ? `?${qs}` : ''}`, {
      method: 'POST',
    });
  }

  public async cancelSales(businessId: string, salesId: string): Promise<SalesResponse> {
    return this.request<SalesResponse>(`/businesses/${businessId}/sales/${salesId}/cancel`, {
      method: 'POST',
    });
  }

  public async listSalesPayments(
    businessId: string,
    salesId: string,
    params?: { page?: number; page_size?: number }
  ): Promise<import('@/types/sales').SalesPaymentListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/sales').SalesPaymentListResponse>(
      `/businesses/${businessId}/sales/${salesId}/payments${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async createSalesPayment(
    businessId: string,
    salesId: string,
    payload: import('@/types/sales').CreateSalesPaymentRequest
  ): Promise<import('@/types/sales').SalesPayment> {
    return this.request<import('@/types/sales').SalesPayment>(
      `/businesses/${businessId}/sales/${salesId}/payments`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  }

  public async cancelSalesPayment(
    businessId: string,
    salesId: string,
    paymentId: string
  ): Promise<import('@/types/sales').SalesPayment> {
    return this.request<import('@/types/sales').SalesPayment>(
      `/businesses/${businessId}/sales/${salesId}/payments/${paymentId}/cancel`,
      { method: 'POST' }
    );
  }

  // Sales Returns
  public async listSalesReturns(
    businessId: string,
    params?: { page?: number; page_size?: number; sales_id?: string; status?: string; search?: string }
  ): Promise<import('@/types/salesReturn').SalesReturnListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
      if (params.sales_id) searchParams.set('sales_id', params.sales_id);
      if (params.status) searchParams.set('status', params.status);
      if (params.search) searchParams.set('search', params.search);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/salesReturn').SalesReturnListResponse>(
      `/businesses/${businessId}/sales-returns${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async createSalesReturn(
    businessId: string,
    payload: import('@/types/salesReturn').SalesReturnCreateInput
  ): Promise<import('@/types/salesReturn').SalesReturnResponse> {
    return this.request<import('@/types/salesReturn').SalesReturnResponse>(
      `/businesses/${businessId}/sales-returns`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async getSalesReturn(
    businessId: string,
    returnId: string
  ): Promise<import('@/types/salesReturn').SalesReturnResponse> {
    return this.request<import('@/types/salesReturn').SalesReturnResponse>(
      `/businesses/${businessId}/sales-returns/${returnId}`,
      { method: 'GET' }
    );
  }

  public async updateSalesReturn(
    businessId: string,
    returnId: string,
    payload: import('@/types/salesReturn').SalesReturnUpdateInput
  ): Promise<import('@/types/salesReturn').SalesReturnResponse> {
    return this.request<import('@/types/salesReturn').SalesReturnResponse>(
      `/businesses/${businessId}/sales-returns/${returnId}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    );
  }

  public async addSalesReturnLine(
    businessId: string,
    returnId: string,
    payload: import('@/types/salesReturn').SalesReturnLineCreateInput
  ): Promise<import('@/types/salesReturn').SalesReturnLineResponse> {
    return this.request<import('@/types/salesReturn').SalesReturnLineResponse>(
      `/businesses/${businessId}/sales-returns/${returnId}/lines`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async updateSalesReturnLine(
    businessId: string,
    returnId: string,
    lineId: string,
    payload: import('@/types/salesReturn').SalesReturnLineUpdateInput
  ): Promise<import('@/types/salesReturn').SalesReturnLineResponse> {
    return this.request<import('@/types/salesReturn').SalesReturnLineResponse>(
      `/businesses/${businessId}/sales-returns/${returnId}/lines/${lineId}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    );
  }

  public async deleteSalesReturnLine(
    businessId: string,
    returnId: string,
    lineId: string
  ): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/businesses/${businessId}/sales-returns/${returnId}/lines/${lineId}`,
      { method: 'DELETE' }
    );
  }

  public async finalizeSalesReturn(
    businessId: string,
    returnId: string
  ): Promise<import('@/types/salesReturn').SalesReturnResponse> {
    return this.request<import('@/types/salesReturn').SalesReturnResponse>(
      `/businesses/${businessId}/sales-returns/${returnId}/finalize`,
      { method: 'POST' }
    );
  }

  public async cancelSalesReturn(
    businessId: string,
    returnId: string
  ): Promise<import('@/types/salesReturn').SalesReturnResponse> {
    return this.request<import('@/types/salesReturn').SalesReturnResponse>(
      `/businesses/${businessId}/sales-returns/${returnId}/cancel`,
      { method: 'POST' }
    );
  }

  // Receivables
  public async listReceivables(
    businessId: string,
    params?: { page?: number; page_size?: number; status?: string; customer_id?: string; branch_id?: string; search?: string }
  ): Promise<import('@/types/receivable').SalesReceivableListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
      if (params.status) searchParams.set('status', params.status);
      if (params.customer_id) searchParams.set('customer_id', params.customer_id);
      if (params.branch_id) searchParams.set('branch_id', params.branch_id);
      if (params.search) searchParams.set('search', params.search);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/receivable').SalesReceivableListResponse>(
      `/businesses/${businessId}/receivables${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getReceivableSummary(
    businessId: string
  ): Promise<import('@/types/receivable').SalesReceivableSummaryResponse> {
    return this.request<import('@/types/receivable').SalesReceivableSummaryResponse>(
      `/businesses/${businessId}/receivables/summary`,
      { method: 'GET' }
    );
  }

  public async getCustomerReceivableSummary(
    businessId: string
  ): Promise<import('@/types/receivable').CustomerReceivableSummaryListResponse> {
    return this.request<import('@/types/receivable').CustomerReceivableSummaryListResponse>(
      `/businesses/${businessId}/receivables/customer-summary`,
      { method: 'GET' }
    );
  }

  public async getReceivableBySalesId(
    businessId: string,
    salesId: string
  ): Promise<import('@/types/receivable').SalesReceivableResponse> {
    return this.request<import('@/types/receivable').SalesReceivableResponse>(
      `/businesses/${businessId}/receivables/${salesId}`,
      { method: 'GET' }
    );
  }

  // Payables
  public async listPayables(
    businessId: string,
    params?: { page?: number; page_size?: number; status?: string; supplier_id?: string; branch_id?: string; search?: string; currency?: string }
  ): Promise<import('@/types/payable').PurchasePayableListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
      if (params.status) searchParams.set('status', params.status);
      if (params.supplier_id) searchParams.set('supplier_id', params.supplier_id);
      if (params.branch_id) searchParams.set('branch_id', params.branch_id);
      if (params.search) searchParams.set('search', params.search);
      if (params.currency) searchParams.set('currency', params.currency);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/payable').PurchasePayableListResponse>(
      `/businesses/${businessId}/purchases/payables${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getPayableSummary(
    businessId: string,
    params?: { supplier_id?: string; branch_id?: string; currency?: string }
  ): Promise<import('@/types/payable').PurchasePayableSummaryResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.supplier_id) searchParams.set('supplier_id', params.supplier_id);
      if (params.branch_id) searchParams.set('branch_id', params.branch_id);
      if (params.currency) searchParams.set('currency', params.currency);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/payable').PurchasePayableSummaryResponse>(
      `/businesses/${businessId}/purchases/payables/summary${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getSupplierPayableSummary(
    businessId: string,
    params?: { currency?: string }
  ): Promise<import('@/types/payable').SupplierPayableSummaryListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.currency) searchParams.set('currency', params.currency);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/payable').SupplierPayableSummaryListResponse>(
      `/businesses/${businessId}/purchases/payables/suppliers/summary${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getPayableByPurchaseId(
    businessId: string,
    purchaseId: string
  ): Promise<import('@/types/payable').PurchasePayableResponse> {
    return this.request<import('@/types/payable').PurchasePayableResponse>(
      `/businesses/${businessId}/purchases/payables/${purchaseId}`,
      { method: 'GET' }
    );
  }

  // ============================================================
  // Aging Reports (Feature #39)
  // ============================================================
  public async getARAging(
    businessId: string,
    params?: { as_of_date?: string; customer_id?: string; branch_id?: string; bucket?: string }
  ): Promise<import('@/types/aging').ARAgingResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.as_of_date) searchParams.set('as_of_date', params.as_of_date);
      if (params.customer_id) searchParams.set('customer_id', params.customer_id);
      if (params.branch_id) searchParams.set('branch_id', params.branch_id);
      if (params.bucket) searchParams.set('bucket', params.bucket);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/aging').ARAgingResponse>(
      `/businesses/${businessId}/receivables/aging${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getAPAging(
    businessId: string,
    params?: { as_of_date?: string; supplier_id?: string; branch_id?: string; bucket?: string }
  ): Promise<import('@/types/aging').APAgingResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.as_of_date) searchParams.set('as_of_date', params.as_of_date);
      if (params.supplier_id) searchParams.set('supplier_id', params.supplier_id);
      if (params.branch_id) searchParams.set('branch_id', params.branch_id);
      if (params.bucket) searchParams.set('bucket', params.bucket);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/aging').APAgingResponse>(
      `/businesses/${businessId}/purchases/payables/aging${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  // Payments
  public async listPayments(
    businessId: string,
    params?: { page?: number; page_size?: number; direction?: string; target_type?: string; target_id?: string }
  ): Promise<import('@/types/payment').PaymentListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
      if (params.direction) searchParams.set('direction', params.direction);
      if (params.target_type) searchParams.set('target_type', params.target_type);
      if (params.target_id) searchParams.set('target_id', params.target_id);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/payment').PaymentListResponse>(
      `/businesses/${businessId}/payments${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async createPayment(
    businessId: string,
    payload: { direction: string; target_type: string; target_id: string; amount: number | string; currency: string; payment_method: string; cash_account_id: string; reference_number?: string; notes?: string; idempotency_key?: string; payment_date?: string }
  ): Promise<import('@/types/payment').Payment> {
    return this.request<import('@/types/payment').Payment>(
      `/businesses/${businessId}/payments`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async getPaymentById(
    businessId: string,
    paymentId: string
  ): Promise<import('@/types/payment').Payment> {
    return this.request<import('@/types/payment').Payment>(
      `/businesses/${businessId}/payments/${paymentId}`,
      { method: 'GET' }
    );
  }

  public async voidPayment(
    businessId: string,
    paymentId: string
  ): Promise<import('@/types/payment').Payment> {
    return this.request<import('@/types/payment').Payment>(
      `/businesses/${businessId}/payments/${paymentId}/void`,
      { method: 'POST' }
    );
  }

  // Accounting
  public async listAccounts(
    businessId: string,
    params?: { account_type?: string }
  ): Promise<import('@/types/accounting').AccountListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.account_type) searchParams.set('account_type', params.account_type);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/accounting').AccountListResponse>(
      `/businesses/${businessId}/accounting/accounts${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async createAccount(
    businessId: string,
    payload: { code: string; name: string; account_type: string; normal_balance?: string; description?: string; parent_id?: string }
  ): Promise<import('@/types/accounting').Account> {
    return this.request<import('@/types/accounting').Account>(
      `/businesses/${businessId}/accounting/accounts`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async archiveAccount(
    businessId: string,
    accountId: string
  ): Promise<import('@/types/accounting').Account> {
    return this.request<import('@/types/accounting').Account>(
      `/businesses/${businessId}/accounting/accounts/${accountId}`,
      { method: 'DELETE' }
    );
  }

  public async createJournal(
    businessId: string,
    payload: { branch_id?: string; journal_date: string; description: string; reference_type?: string; reference_id?: string; lines: { account_id: string; description?: string; debit: number | string; credit: number | string }[]; idempotency_key?: string }
  ): Promise<import('@/types/accounting').JournalEntry> {
    return this.request<import('@/types/accounting').JournalEntry>(
      `/businesses/${businessId}/accounting/journals`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async listJournals(
    businessId: string,
    params?: { branch_id?: string; status?: string; page?: number; page_size?: number }
  ): Promise<import('@/types/accounting').JournalEntryListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.branch_id) searchParams.set('branch_id', params.branch_id);
      if (params.status) searchParams.set('status', params.status);
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/accounting').JournalEntryListResponse>(
      `/businesses/${businessId}/accounting/journals${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getJournal(
    businessId: string,
    journalId: string
  ): Promise<import('@/types/accounting').JournalEntry> {
    return this.request<import('@/types/accounting').JournalEntry>(
      `/businesses/${businessId}/accounting/journals/${journalId}`,
      { method: 'GET' }
    );
  }

  public async voidJournal(
    businessId: string,
    journalId: string
  ): Promise<import('@/types/accounting').JournalEntry> {
    return this.request<import('@/types/accounting').JournalEntry>(
      `/businesses/${businessId}/accounting/journals/${journalId}/void`,
      { method: 'POST' }
    );
  }

  public async getTrialBalance(
    businessId: string
  ): Promise<import('@/types/accounting').TrialBalanceResponse> {
    return this.request<import('@/types/accounting').TrialBalanceResponse>(
      `/businesses/${businessId}/accounting/trial-balance`,
      { method: 'GET' }
    );
  }

  // Cash Accounts
  public async listCashAccounts(
    businessId: string,
    params?: { page?: number; page_size?: number; search?: string; account_type?: string; status?: string }
  ): Promise<import('@/types/cashAccount').CashAccountListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
      if (params.search) searchParams.set('search', params.search);
      if (params.account_type) searchParams.set('account_type', params.account_type);
      if (params.status) searchParams.set('status', params.status);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/cashAccount').CashAccountListResponse>(
      `/businesses/${businessId}/cash-accounts${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getCashAccountsSummary(
    businessId: string
  ): Promise<import('@/types/cashAccount').CashSummaryResponse> {
    return this.request<import('@/types/cashAccount').CashSummaryResponse>(
      `/businesses/${businessId}/cash-accounts/summary`,
      { method: 'GET' }
    );
  }

  public async getCashAccount(
    businessId: string,
    accountId: string
  ): Promise<import('@/types/cashAccount').CashAccountResponse> {
    return this.request<import('@/types/cashAccount').CashAccountResponse>(
      `/businesses/${businessId}/cash-accounts/${accountId}`,
      { method: 'GET' }
    );
  }

  public async createCashAccount(
    businessId: string,
    payload: import('@/types/cashAccount').CashAccountCreateInput
  ): Promise<import('@/types/cashAccount').CashAccountResponse> {
    return this.request<import('@/types/cashAccount').CashAccountResponse>(
      `/businesses/${businessId}/cash-accounts`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async updateCashAccount(
    businessId: string,
    accountId: string,
    payload: import('@/types/cashAccount').CashAccountUpdateInput
  ): Promise<import('@/types/cashAccount').CashAccountResponse> {
    return this.request<import('@/types/cashAccount').CashAccountResponse>(
      `/businesses/${businessId}/cash-accounts/${accountId}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    );
  }

  public async activateCashAccount(
    businessId: string,
    accountId: string
  ): Promise<import('@/types/cashAccount').CashAccountResponse> {
    return this.request<import('@/types/cashAccount').CashAccountResponse>(
      `/businesses/${businessId}/cash-accounts/${accountId}/activate`,
      { method: 'POST' }
    );
  }

  public async deactivateCashAccount(
    businessId: string,
    accountId: string
  ): Promise<import('@/types/cashAccount').CashAccountResponse> {
    return this.request<import('@/types/cashAccount').CashAccountResponse>(
      `/businesses/${businessId}/cash-accounts/${accountId}/deactivate`,
      { method: 'POST' }
    );
  }

  public async createCashMovement(
    businessId: string,
    accountId: string,
    payload: import('@/types/cashAccount').CashMovementCreateInput
  ): Promise<import('@/types/cashAccount').CashMovementResponse> {
    return this.request<import('@/types/cashAccount').CashMovementResponse>(
      `/businesses/${businessId}/cash-accounts/${accountId}/movements`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async listCashMovements(
    businessId: string,
    accountId: string,
    params?: { page?: number; page_size?: number; movement_type?: string; date_from?: string; date_to?: string }
  ): Promise<import('@/types/cashAccount').CashMovementListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
      if (params.movement_type) searchParams.set('movement_type', params.movement_type);
      if (params.date_from) searchParams.set('date_from', params.date_from);
      if (params.date_to) searchParams.set('date_to', params.date_to);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/cashAccount').CashMovementListResponse>(
      `/businesses/${businessId}/cash-accounts/${accountId}/movements${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async createCashTransfer(
    businessId: string,
    payload: import('@/types/cashAccount').CashTransferInput
  ): Promise<import('@/types/cashAccount').CashMovementResponse[]> {
    return this.request<import('@/types/cashAccount').CashMovementResponse[]>(
      `/businesses/${businessId}/cash-accounts/transfers`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  // --- Expense Category ---

  public async listExpenseCategories(
    businessId: string,
    params?: { page?: number; page_size?: number; search?: string; status?: string }
  ): Promise<import('@/types/expense').ExpenseCategoryListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
      if (params.search) searchParams.set('search', params.search);
      if (params.status) searchParams.set('status', params.status);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/expense').ExpenseCategoryListResponse>(
      `/businesses/${businessId}/expense-categories${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async createExpenseCategory(
    businessId: string,
    payload: import('@/types/expense').ExpenseCategoryCreateInput
  ): Promise<import('@/types/expense').ExpenseCategoryResponse> {
    return this.request<import('@/types/expense').ExpenseCategoryResponse>(
      `/businesses/${businessId}/expense-categories`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async archiveExpenseCategory(
    businessId: string,
    categoryId: string
  ): Promise<import('@/types/expense').ExpenseCategoryResponse> {
    return this.request<import('@/types/expense').ExpenseCategoryResponse>(
      `/businesses/${businessId}/expense-categories/${categoryId}/archive`,
      { method: 'POST' }
    );
  }

  // --- Expense ---

  public async listExpenses(
    businessId: string,
    params?: { page?: number; page_size?: number; search?: string; status?: string; category_id?: string; date_from?: string; date_to?: string }
  ): Promise<import('@/types/expense').ExpenseListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.page) searchParams.set('page', String(params.page));
      if (params.page_size) searchParams.set('page_size', String(params.page_size));
      if (params.search) searchParams.set('search', params.search);
      if (params.status) searchParams.set('status', params.status);
      if (params.category_id) searchParams.set('category_id', params.category_id);
      if (params.date_from) searchParams.set('date_from', params.date_from);
      if (params.date_to) searchParams.set('date_to', params.date_to);
    }
    const qs = searchParams.toString();
    return this.request<import('@/types/expense').ExpenseListResponse>(
      `/businesses/${businessId}/expenses${qs ? `?${qs}` : ''}`,
      { method: 'GET' }
    );
  }

  public async getExpenseSummary(
    businessId: string
  ): Promise<import('@/types/expense').ExpenseSummaryResponse> {
    return this.request<import('@/types/expense').ExpenseSummaryResponse>(
      `/businesses/${businessId}/expenses/summary`,
      { method: 'GET' }
    );
  }

  public async getExpense(
    businessId: string,
    expenseId: string
  ): Promise<import('@/types/expense').ExpenseResponse> {
    return this.request<import('@/types/expense').ExpenseResponse>(
      `/businesses/${businessId}/expenses/${expenseId}`,
      { method: 'GET' }
    );
  }

  public async createExpense(
    businessId: string,
    payload: import('@/types/expense').ExpenseCreateInput
  ): Promise<import('@/types/expense').ExpenseResponse> {
    return this.request<import('@/types/expense').ExpenseResponse>(
      `/businesses/${businessId}/expenses`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async updateExpense(
    businessId: string,
    expenseId: string,
    payload: import('@/types/expense').ExpenseUpdateInput
  ): Promise<import('@/types/expense').ExpenseResponse> {
    return this.request<import('@/types/expense').ExpenseResponse>(
      `/businesses/${businessId}/expenses/${expenseId}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    );
  }

  public async finalizeExpense(
    businessId: string,
    expenseId: string
  ): Promise<import('@/types/expense').ExpenseResponse> {
    return this.request<import('@/types/expense').ExpenseResponse>(
      `/businesses/${businessId}/expenses/${expenseId}/finalize`,
      { method: 'POST' }
    );
  }

  public async cancelExpense(
    businessId: string,
    expenseId: string
  ): Promise<import('@/types/expense').ExpenseResponse> {
    return this.request<import('@/types/expense').ExpenseResponse>(
      `/businesses/${businessId}/expenses/${expenseId}/cancel`,
      { method: 'POST' }
    );
  }

  // ============================================================
  // Accounting Period
  // ============================================================
  public async listPeriods(
    businessId: string
  ): Promise<import('@/types/accounting').AccountingPeriodListResponse> {
    return this.request<import('@/types/accounting').AccountingPeriodListResponse>(
      `/businesses/${businessId}/accounting/periods`,
      { method: 'GET' }
    );
  }

  public async getPeriod(
    businessId: string,
    periodId: string
  ): Promise<import('@/types/accounting').AccountingPeriod> {
    return this.request<import('@/types/accounting').AccountingPeriod>(
      `/businesses/${businessId}/accounting/periods/${periodId}`,
      { method: 'GET' }
    );
  }

  public async createPeriod(
    businessId: string,
    payload: import('@/types/accounting').AccountingPeriodCreatePayload
  ): Promise<import('@/types/accounting').AccountingPeriod> {
    return this.request<import('@/types/accounting').AccountingPeriod>(
      `/businesses/${businessId}/accounting/periods`,
      { method: 'POST', body: JSON.stringify(payload) }
    );
  }

  public async closePeriod(
    businessId: string,
    periodId: string
  ): Promise<import('@/types/accounting').AccountingPeriod> {
    return this.request<import('@/types/accounting').AccountingPeriod>(
      `/businesses/${businessId}/accounting/periods/${periodId}/close`,
      { method: 'POST' }
    );
  }

  // ============================================================
  // Financial Reports (Feature #36)
  // ============================================================
  public async getProfitAndLoss(
    businessId: string,
    periodId: string
  ): Promise<import('@/types/accounting').ProfitAndLossResponse> {
    return this.request<import('@/types/accounting').ProfitAndLossResponse>(
      `/businesses/${businessId}/accounting/reports/profit-and-loss?period_id=${periodId}`,
      { method: 'GET' }
    );
  }

  public async getBalanceSheet(
    businessId: string,
    periodId: string
  ): Promise<import('@/types/accounting').BalanceSheetResponse> {
    return this.request<import('@/types/accounting').BalanceSheetResponse>(
      `/businesses/${businessId}/accounting/reports/balance-sheet?period_id=${periodId}`,
      { method: 'GET' }
    );
  }

  public async getTaxSummary(
    businessId: string,
    year: number,
    month: number
  ): Promise<import('@/types/accounting').TaxSummaryResponse> {
    return this.request<import('@/types/accounting').TaxSummaryResponse>(
      `/businesses/${businessId}/accounting/reports/tax-summary?year=${year}&month=${month}`,
      { method: 'GET' }
    );
  }

  // ============================================================
  // STOCK CARD (Feature #42)
  // ============================================================
  public async getStockCard(
    businessId: string,
    params: { location_id: string; product_id: string; variant_id?: string; date_from?: string; date_to?: string; page?: number; page_size?: number }
  ): Promise<StockCardResponse> {
    const searchParams = new URLSearchParams();
    searchParams.set('location_id', params.location_id);
    searchParams.set('product_id', params.product_id);
    if (params.variant_id) searchParams.set('variant_id', params.variant_id);
    if (params.date_from) searchParams.set('date_from', params.date_from);
    if (params.date_to) searchParams.set('date_to', params.date_to);
    if (params.page) searchParams.set('page', String(params.page));
    if (params.page_size) searchParams.set('page_size', String(params.page_size));
    return this.request<StockCardResponse>(
      `/businesses/${businessId}/inventory/stock-cards?${searchParams.toString()}`,
      { method: 'GET' }
    );
  }
}

// ============================================================
// STOCK CARD TYPES (Feature #42)
// ============================================================
export interface StockCardLineResponse {
  transaction_date: string;
  movement_type: string;
  reference_id: string;
  reference_number?: string | null;
  notes?: string | null;
  qty_in: string;
  qty_out: string;
  unit_cost: string;
  movement_value: string;
  running_quantity: string;
  running_valuation: string;
}

export interface StockCardResponse {
  business_id: string;
  location_id: string;
  location_name?: string | null;
  product_id: string;
  product_name?: string | null;
  variant_id?: string | null;
  variant_name?: string | null;
  unit_code?: string | null;
  date_range: { start_date: string; end_date: string };
  opening_quantity: string;
  opening_unit_cost: string;
  opening_valuation: string;
  lines: StockCardLineResponse[];
  total_qty_in: string;
  total_qty_out: string;
  total_in_value: string;
  total_out_value: string;
  closing_quantity: string;
  closing_valuation: string;
  page: number;
  page_size: number;
  total_items: number;
}

export const apiClient = new ApiClient();
