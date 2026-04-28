variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "spotify_client_id" {
  description = "Spotify API client ID"
  type        = string
  sensitive   = true
}

variable "spotify_client_secret" {
  description = "Spotify API client secret"
  type        = string
  sensitive   = true
}

variable "spotify_refresh_token" {
  description = "Spotify refresh token"
  type        = string
  sensitive   = true
}
