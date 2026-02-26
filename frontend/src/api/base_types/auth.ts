/** POST /auth/login request body */
export interface LoginRequest {
  email: string;
  password: string;
}

/** POST /auth/login response */
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
  role: string | null;
}

/** Shape of the user stored in AuthContext */
export interface AuthUser {
  user_id: number;
  username: string;
  email: string;
  role: string | null;
}
