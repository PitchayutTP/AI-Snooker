import React from "react";
import Button from "../components/Button";

export default function Login({ onLogin }) {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-xl shadow-md border">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto bg-black rounded-xl flex items-center justify-center text-white font-bold mb-4">
            LOGO
          </div>
          <h2 className="text-2xl font-bold text-gray-900">LOGIN</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              User ID
            </label>
            <input
              type="text"
              placeholder="Enter user id or email"
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              placeholder="Enter password"
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
            />
          </div>

          <Button onClick={onLogin} className="w-full">
            👉 Login
          </Button>

          <div className="flex justify-between text-sm pt-2">
            <button className="text-gray-500 hover:text-black">
              Reset Password
            </button>
            <button className="text-gray-500 hover:text-black">
              Create account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
